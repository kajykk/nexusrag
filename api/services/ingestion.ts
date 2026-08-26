/**
 * 文档摄取服务 - 后台串行处理队列
 *
 * 解析 / 分块 / Embedding 属于 CPU 与 IO 密集操作，全局串行化可避免
 * 多文件并发摄取耗尽事件循环与上游 API 配额，同时保证 BM25 / 向量库
 * 缓存更新的顺序性。响应不阻塞：入队后立即返回。
 */
import fs from 'fs'
import db from '../db.js'
import { ingestDocument } from '../rag/pipeline.js'

let ingestChain: Promise<void> = Promise.resolve()

export function enqueueIngestion(
  kbId: string,
  docId: string,
  filePath: string,
  fileType: string,
): void {
  ingestChain = ingestChain
    .then(async () => {
      try {
        db.prepare(`UPDATE documents SET status = 'processing' WHERE id = ?`).run(docId)
        await ingestDocument(kbId, docId, filePath, fileType)
        // 更新知识库文档计数
        db.prepare(`
          UPDATE knowledge_bases
          SET document_count = (SELECT COUNT(*) FROM documents WHERE kb_id = ?)
          WHERE id = ?
        `).run(kbId, kbId)
      } catch (err) {
        // 错误细节仅记录服务端日志，入库对外展示脱敏文案
        console.error(`文档处理失败 ${docId}:`, err)
        db.prepare(`
          UPDATE documents SET status = 'failed', error = ? WHERE id = ?
        `).run('文档处理失败，请检查文件内容后重试', docId)
      } finally {
        // 删除临时文件（忽略删除失败，文件可能已被清理）
        try { fs.unlinkSync(filePath) } catch { /* 临时文件清理失败可忽略 */ }
      }
    })
    .catch((err) => {
      // 兜底：保证队列链条永不中断
      console.error('Ingestion queue error:', err)
    })
}

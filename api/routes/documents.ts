/**
 * 文档路由 - 上传、列表、删除、状态查询
 */
import { Router, type Response } from 'express'
import multer from 'multer'
import path from 'path'
import fs from 'fs'
import { v4 as uuid } from 'uuid'
import db from '../db.js'
import { config } from '../config.js'
import { authMiddleware, type AuthRequest } from '../middleware/auth.js'
import { ingestDocument } from '../rag/pipeline.js'
import * as vectorStore from '../rag/vectorStore.js'
import * as bm25 from '../rag/bm25.js'
import type { Document } from '../types/index.js'

const router = Router({ mergeParams: true })

const upload = multer({
  storage: multer.diskStorage({
    destination: (_req, _file, cb) => {
      const dir = config.storage.uploadPath
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })
      cb(null, dir)
    },
    filename: (_req, file, cb) => {
      const ext = path.extname(file.originalname)
      cb(null, `${uuid()}${ext}`)
    },
  }),
  limits: { fileSize: 50 * 1024 * 1024 },  // 50MB
  fileFilter: (_req, file, cb) => {
    const allowed = ['.pdf', '.docx', '.doc', '.md', '.markdown', '.txt']
    const ext = path.extname(file.originalname).toLowerCase()
    cb(null, allowed.includes(ext))
  },
})

router.use(authMiddleware)

/**
 * 文档列表
 */
router.get('/', (req: AuthRequest, res: Response): void => {
  const docs = db.prepare(`
    SELECT * FROM documents WHERE kb_id = ? ORDER BY created_at DESC
  `).all(req.params.kbId) as Document[]

  res.json({ success: true, data: docs })
})

/**
 * 上传文档（支持多文件）
 */
router.post('/', upload.array('files', 10), async (req: AuthRequest, res: Response): Promise<void> => {
  const kbId = req.params.kbId
  const files = req.files as Express.Multer.File[] | undefined
  if (!files || files.length === 0) {
    res.status(400).json({ success: false, error: '请上传文件' })
    return
  }

  // 校验知识库归属
  const kb = db.prepare('SELECT id FROM knowledge_bases WHERE id = ? AND user_id = ?').get(kbId, req.userId)
  if (!kb) {
    res.status(404).json({ success: false, error: '知识库不存在' })
    return
  }

  const results: Document[] = []
  for (const file of files) {
    const docId = uuid()
    const ext = path.extname(file.originalname).toLowerCase().slice(1)
    db.prepare(`
      INSERT INTO documents (id, kb_id, name, file_type, file_size, status)
      VALUES (?, ?, ?, ?, ?, 'pending')
    `).run(docId, kbId, file.originalname, ext, file.size)

    const doc = db.prepare('SELECT * FROM documents WHERE id = ?').get(docId) as Document
    results.push(doc)

    // 异步处理文档（不阻塞响应）
    setImmediate(async () => {
      try {
        db.prepare(`UPDATE documents SET status = 'processing' WHERE id = ?`).run(docId)
        await ingestDocument(kbId, docId, file.path, ext)
        // 更新文档计数
        db.prepare(`
          UPDATE knowledge_bases
          SET document_count = (SELECT COUNT(*) FROM documents WHERE kb_id = ?)
          WHERE id = ?
        `).run(kbId, kbId)
      } catch (err) {
        db.prepare(`
          UPDATE documents SET status = 'failed', error = ? WHERE id = ?
        `).run((err as Error).message, docId)
        console.error(`文档处理失败 ${docId}:`, err)
      } finally {
        // 删除临时文件（忽略删除失败，文件可能已被清理）
        try { fs.unlinkSync(file.path) } catch { /* 临时文件清理失败可忽略 */ }
      }
    })
  }

  res.json({ success: true, data: results })
})

/**
 * 文档状态
 */
router.get('/:docId/status', (req: AuthRequest, res: Response): void => {
  const doc = db.prepare(`
    SELECT id, status, chunk_count, error FROM documents WHERE id = ? AND kb_id = ?
  `).get(req.params.docId, req.params.kbId) as { id: string; status: string; chunk_count: number; error?: string } | undefined

  if (!doc) {
    res.status(404).json({ success: false, error: '文档不存在' })
    return
  }

  res.json({ success: true, data: doc })
})

/**
 * 删除文档 - 同时清理向量和 BM25 索引
 */
router.delete('/:docId', (req: AuthRequest, res: Response): void => {
  const doc = db.prepare(`
    SELECT d.id, d.kb_id FROM documents d
    JOIN knowledge_bases k ON d.kb_id = k.id
    WHERE d.id = ? AND d.kb_id = ? AND k.user_id = ?
  `).get(req.params.docId, req.params.kbId, req.userId) as { id: string; kb_id: string } | undefined

  if (!doc) {
    res.status(404).json({ success: false, error: '文档不存在' })
    return
  }

  // 获取该文档所有 chunkId
  const chunks = db.prepare('SELECT id FROM chunks WHERE doc_id = ?').all(req.params.docId) as { id: string }[]
  const chunkIds = chunks.map((c) => c.id)

  // 删除数据库记录
  db.prepare('DELETE FROM documents WHERE id = ?').run(req.params.docId)

  // 删除向量
  if (chunkIds.length > 0) {
    vectorStore.removeByDoc(req.params.kbId, req.params.docId, chunkIds)
  }
  // 清空 BM25 缓存（重建）
  bm25.clearCache(req.params.kbId)

  // 更新文档计数
  db.prepare(`
    UPDATE knowledge_bases
    SET document_count = (SELECT COUNT(*) FROM documents WHERE kb_id = ?)
    WHERE id = ?
  `).run(req.params.kbId, req.params.kbId)

  res.json({ success: true })
})

export default router

/**
 * RAG Pipeline 回归测试
 */
import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'
import db from '../api/db.js'
import * as vectorStore from '../api/rag/vectorStore.js'
import { ingestDocument, rerank } from '../api/rag/pipeline.js'
import type { RetrievedChunk } from '../api/types/index.js'

describe('rerank（中文重叠度）', () => {
  function mk(id: string, content: string): RetrievedChunk {
    return {
      chunk: {
        id,
        doc_id: 'doc-1',
        chunk_index: 0,
        content,
        vector_id: '',
        token_count: 0,
        metadata: {},
      },
      doc: {
        id: 'doc-1',
        kb_id: 'kb-1',
        name: 'doc.md',
        file_type: 'md',
        file_size: 0,
        status: 'ready',
        chunk_count: 1,
        created_at: '',
      },
      score: 0.5,
    }
  }

  it('中文查询时含关键词的片段应排在前面', () => {
    // 回归：旧实现按空格分词，中文查询重叠度恒为 0，排序失效
    const results = [mk('a', '完全无关的随机内容段落'), mk('b', '机器学习是人工智能的一个重要分支')]
    const ranked = rerank('机器学习', results)
    expect(ranked[0].chunk.id).toBe('b')
    expect(ranked[0].score).toBeGreaterThan(ranked[1].score)
  })

  it('查询无命中时保持稳定排序', () => {
    const results = [mk('a', '内容甲'), mk('b', '内容乙')]
    const ranked = rerank('量子计算', results)
    expect(ranked.map((r) => r.chunk.id)).toEqual(['a', 'b'])
  })
})

describe('ingestDocument', () => {
  it('写入 DB 的 vector_id 与向量库实际位置一致', async () => {
    const kbId = `test-kb-pipeline-${Date.now()}`
    // 预置一个已有向量，验证基数偏移正确
    vectorStore.addVectors(kbId, [{ chunkId: 'seed', vector: [0.1, 0.2, 0.3] }])

    const docId = `doc-pipe-${Date.now()}`
    db.prepare(
      "INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)",
    ).run(`u-${kbId}`, `${kbId}@test.local`, 'x', 'tester')
    db.prepare(`
      INSERT INTO knowledge_bases (id, user_id, name) VALUES (?, ?, ?)
    `).run(kbId, `u-${kbId}`, 'pipeline-test-kb')
    db.prepare(`
      INSERT INTO documents (id, kb_id, name, file_type, status)
      VALUES (?, ?, ?, ?, 'pending')
    `).run(docId, kbId, 'pipe-test.md', 'md')

    const uploadDir = process.env.UPLOAD_PATH || './data/test/uploads'
    fs.mkdirSync(uploadDir, { recursive: true })
    const mdPath = path.join(uploadDir, `pipe-test-${Date.now()}.md`)
    fs.writeFileSync(mdPath, '# 测试文档\n\n第一段测试内容，用于生成有效分块。\n\n第二段测试内容。')

    try {
      const { chunkCount } = await ingestDocument(kbId, docId, mdPath, 'md')
      expect(chunkCount).toBeGreaterThan(0)

      const rows = db.prepare(
        'SELECT id, vector_id FROM chunks WHERE doc_id = ? ORDER BY chunk_index',
      ).all(docId) as { id: string; vector_id: string }[]
      expect(rows.length).toBe(chunkCount)

      // 向量库按位置存储 chunkId；DB 的 vector_id 应与位置一一对应：
      // vector_id "vec_<n>" 对应 getIndex(kbId).chunkIds[<n>]
      const storeChunkIds = vectorStore.getIndex(kbId).chunkIds
      const seedCount = 1
      rows.forEach((row, i) => {
        expect(row.vector_id).toBe(`vec_${seedCount + i}`)
        expect(storeChunkIds[seedCount + i]).toBe(row.id)
      })
    } finally {
      fs.rmSync(mdPath, { force: true })
      vectorStore.deleteIndex(kbId)
    }
  })
})

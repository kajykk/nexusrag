/**
 * 知识库路由
 */
import { Router, type Response } from 'express'
import { v4 as uuid } from 'uuid'
import { z } from 'zod'
import db from '../db.js'
import { authMiddleware, type AuthRequest } from '../middleware/auth.js'
import * as vectorStore from '../rag/vectorStore.js'
import * as bm25 from '../rag/bm25.js'
import type { KnowledgeBase } from '../types/index.js'

const router = Router()

const createSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional().default(''),
})

const updateSchema = z.object({
  name: z.string().min(1).max(100).optional(),
  description: z.string().max(500).optional(),
})

router.use(authMiddleware)

/**
 * 列表
 */
router.get('/', (req: AuthRequest, res: Response): void => {
  const kbs = db.prepare(`
    SELECT * FROM knowledge_bases WHERE user_id = ? ORDER BY created_at DESC
  `).all(req.userId) as KnowledgeBase[]

  res.json({ success: true, data: kbs })
})

/**
 * 详情
 */
router.get('/:id', (req: AuthRequest, res: Response): void => {
  const kb = db.prepare(`
    SELECT * FROM knowledge_bases WHERE id = ? AND user_id = ?
  `).get(req.params.id, req.userId) as KnowledgeBase | undefined

  if (!kb) {
    res.status(404).json({ success: false, error: '知识库不存在' })
    return
  }

  // 统计向量数
  const vecCount = vectorStore.count(kb.id)

  res.json({ success: true, data: { ...kb, vectorCount: vecCount } })
})

/**
 * 创建
 */
router.post('/', (req: AuthRequest, res: Response): void => {
  const parsed = createSchema.safeParse(req.body)
  if (!parsed.success) {
    res.status(400).json({ success: false, error: parsed.error.issues[0]?.message })
    return
  }

  const id = uuid()
  db.prepare(`
    INSERT INTO knowledge_bases (id, user_id, name, description) VALUES (?, ?, ?, ?)
  `).run(id, req.userId, parsed.data.name, parsed.data.description)

  const kb = db.prepare('SELECT * FROM knowledge_bases WHERE id = ?').get(id) as KnowledgeBase
  res.json({ success: true, data: kb })
})

/**
 * 删除 - 同时清理向量库和 BM25 缓存
 */
router.delete('/:id', (req: AuthRequest, res: Response): void => {
  const kb = db.prepare('SELECT id FROM knowledge_bases WHERE id = ? AND user_id = ?').get(req.params.id, req.userId)
  if (!kb) {
    res.status(404).json({ success: false, error: '知识库不存在' })
    return
  }

  db.prepare('DELETE FROM knowledge_bases WHERE id = ?').run(req.params.id)
  vectorStore.deleteIndex(req.params.id)
  bm25.clearCache(req.params.id)

  res.json({ success: true })
})

/**
 * 更新
 */
router.patch('/:id', (req: AuthRequest, res: Response): void => {
  const parsed = updateSchema.safeParse(req.body)
  if (!parsed.success) {
    res.status(400).json({ success: false, error: parsed.error.issues[0]?.message })
    return
  }

  const kb = db.prepare('SELECT id FROM knowledge_bases WHERE id = ? AND user_id = ?').get(req.params.id, req.userId)
  if (!kb) {
    res.status(404).json({ success: false, error: '知识库不存在' })
    return
  }

  const { name, description } = parsed.data
  if (name !== undefined) db.prepare('UPDATE knowledge_bases SET name = ? WHERE id = ?').run(name, req.params.id)
  if (description !== undefined) {
    db.prepare('UPDATE knowledge_bases SET description = ? WHERE id = ?').run(description, req.params.id)
  }

  const updated = db.prepare('SELECT * FROM knowledge_bases WHERE id = ?').get(req.params.id) as KnowledgeBase
  res.json({ success: true, data: updated })
})

export default router

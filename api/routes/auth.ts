/**
 * 认证路由 - 注册 / 登录 / 当前用户
 */
import { Router, type Response } from 'express'
import bcrypt from 'bcryptjs'
import { v4 as uuid } from 'uuid'
import { z } from 'zod'
import db from '../db.js'
import { generateToken, type AuthRequest, authMiddleware } from '../middleware/auth.js'
import type { User } from '../types/index.js'

const router = Router()

const registerSchema = z.object({
  email: z.string().email(),
  password: z.string().min(6).max(64),
  name: z.string().min(1).max(50),
})

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string(),
})

/**
 * 注册
 */
router.post('/register', async (req: AuthRequest, res: Response): Promise<void> => {
  try {
    const parsed = registerSchema.safeParse(req.body)
    if (!parsed.success) {
      res.status(400).json({ success: false, error: parsed.error.issues[0]?.message })
      return
    }
    const { email, password, name } = parsed.data

    // 检查邮箱是否已注册
    const existing = db.prepare('SELECT id FROM users WHERE email = ?').get(email)
    if (existing) {
      res.status(409).json({ success: false, error: '邮箱已被注册' })
      return
    }

    // 创建用户
    const id = uuid()
    const passwordHash = await bcrypt.hash(password, 10)
    db.prepare(`
      INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)
    `).run(id, email, passwordHash, name)

    const user = db.prepare('SELECT id, email, name, created_at FROM users WHERE id = ?').get(id) as User
    const token = generateToken({ id: user.id, email: user.email })

    res.json({ success: true, data: { user, token } })
  } catch (err) {
    res.status(500).json({ success: false, error: (err as Error).message })
  }
})

/**
 * 登录
 */
router.post('/login', async (req: AuthRequest, res: Response): Promise<void> => {
  try {
    const parsed = loginSchema.safeParse(req.body)
    if (!parsed.success) {
      res.status(400).json({ success: false, error: parsed.error.issues[0]?.message })
      return
    }
    const { email, password } = parsed.data

    const row = db.prepare('SELECT * FROM users WHERE email = ?').get(email) as (User & { password_hash: string }) | undefined
    if (!row) {
      res.status(401).json({ success: false, error: '邮箱或密码错误' })
      return
    }

    const ok = await bcrypt.compare(password, row.password_hash)
    if (!ok) {
      res.status(401).json({ success: false, error: '邮箱或密码错误' })
      return
    }

    const token = generateToken({ id: row.id, email: row.email })
    const { password_hash: _password_hash, ...user } = row

    res.json({ success: true, data: { user, token } })
  } catch (err) {
    res.status(500).json({ success: false, error: (err as Error).message })
  }
})

/**
 * 获取当前用户
 */
router.get('/me', authMiddleware, (req: AuthRequest, res: Response): void => {
  const user = db.prepare('SELECT id, email, name, created_at FROM users WHERE id = ?').get(req.userId) as User | undefined
  if (!user) {
    res.status(404).json({ success: false, error: '用户不存在' })
    return
  }
  res.json({ success: true, data: user })
})

/**
 * 创建演示账号（一键体验，无需注册）
 */
router.post('/demo', async (_req: AuthRequest, res: Response): Promise<void> => {
  try {
    // 检查是否已有 demo 账号
    let user = db.prepare('SELECT id, email, name, created_at FROM users WHERE email = ?').get('demo@nexusrag.ai') as User | undefined

    if (!user) {
      const id = uuid()
      const passwordHash = await bcrypt.hash('demo123456', 10)
      db.prepare(`
        INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)
      `).run(id, 'demo@nexusrag.ai', passwordHash, '演示用户')
      user = db.prepare('SELECT id, email, name, created_at FROM users WHERE id = ?').get(id) as User
    }

    const token = generateToken({ id: user!.id, email: user!.email })
    res.json({ success: true, data: { user, token } })
  } catch (err) {
    res.status(500).json({ success: false, error: (err as Error).message })
  }
})

export default router

/**
 * 对话路由 - 会话管理 + SSE 流式问答
 */
import { Router, type Response } from 'express'
import { v4 as uuid } from 'uuid'
import db from '../db.js'
import { authMiddleware, type AuthRequest } from '../middleware/auth.js'
import { ragAnswer } from '../rag/pipeline.js'
import { runAgentWorkflow } from '../agents/workflow.js'
import * as bm25 from '../rag/bm25.js'
import type { ChatMessage, ChatSession, Citation, StreamChunk } from '../types/index.js'

const router = Router({ mergeParams: true })

router.use(authMiddleware)

/**
 * 创建会话
 */
router.post('/sessions', (req: AuthRequest, res: Response): void => {
  const kbId = req.params.kbId
  const { title, mode } = req.body

  const kb = db.prepare('SELECT id FROM knowledge_bases WHERE id = ? AND user_id = ?').get(kbId, req.userId)
  if (!kb) {
    res.status(404).json({ success: false, error: '知识库不存在' })
    return
  }

  const id = uuid()
  db.prepare(`
    INSERT INTO chat_sessions (id, kb_id, user_id, title, mode) VALUES (?, ?, ?, ?, ?)
  `).run(id, kbId, req.userId, title || '新对话', mode || 'normal')

  const session = db.prepare('SELECT * FROM chat_sessions WHERE id = ?').get(id) as ChatSession
  res.json({ success: true, data: session })
})

/**
 * 会话列表
 */
router.get('/sessions', (req: AuthRequest, res: Response): void => {
  const sessions = db.prepare(`
    SELECT * FROM chat_sessions WHERE kb_id = ? AND user_id = ? ORDER BY created_at DESC
  `).all(req.params.kbId, req.userId) as ChatSession[]

  res.json({ success: true, data: sessions })
})

/**
 * 消息历史
 */
router.get('/sessions/:sid/messages', (req: AuthRequest, res: Response): void => {
  const messages = db.prepare(`
    SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC
  `).all(req.params.sid) as ChatMessage[]

  // 反序列化 citations（DB 中以 JSON 字符串存储）
  const parsed = messages.map((m): ChatMessage => ({
    ...m,
    citations: m.citations ? (JSON.parse(m.citations as unknown as string) as Citation[]) : undefined,
  }))

  res.json({ success: true, data: parsed })
})

/**
 * 删除会话
 */
router.delete('/sessions/:sid', (req: AuthRequest, res: Response): void => {
  db.prepare('DELETE FROM chat_sessions WHERE id = ? AND user_id = ?').run(req.params.sid, req.userId)
  res.json({ success: true })
})

/**
 * 发送消息 - SSE 流式响应
 *
 * 响应格式（Server-Sent Events）:
 * data: {"type":"status","data":{"status":"正在检索..."}}
 * data: {"type":"citation","data":{"citations":[...]}}
 * data: {"type":"token","data":{"content":"回答"}}
 * data: {"type":"done","data":{}}
 */
router.post('/sessions/:sid/messages', async (req: AuthRequest, res: Response): Promise<void> => {
  const sid = req.params.sid
  const { content, mode, topK } = req.body

  if (!content || typeof content !== 'string') {
    res.status(400).json({ success: false, error: '消息内容不能为空' })
    return
  }

  // 查会话
  const session = db.prepare(`
    SELECT s.*, k.user_id as kb_user_id FROM chat_sessions s
    JOIN knowledge_bases k ON s.kb_id = k.id
    WHERE s.id = ? AND k.user_id = ?
  `).get(sid, req.userId) as (ChatSession & { kb_user_id: string }) | undefined

  if (!session) {
    res.status(404).json({ success: false, error: '会话不存在' })
    return
  }

  // 检查知识库是否有文档
  bm25.clearCache(session.kb_id)

  // 设置 SSE 头
  res.setHeader('Content-Type', 'text/event-stream')
  res.setHeader('Cache-Control', 'no-cache')
  res.setHeader('Connection', 'keep-alive')
  res.setHeader('X-Accel-Buffering', 'no')
  res.flushHeaders?.()

  const send = (chunk: StreamChunk) => {
    res.write(`data: ${JSON.stringify(chunk)}\n\n`)
  }

  try {
    // 保存用户消息
    const userMsgId = uuid()
    db.prepare(`
      INSERT INTO chat_messages (id, session_id, role, content) VALUES (?, ?, 'user', ?)
    `).run(userMsgId, sid, content)

    // 第一条消息自动更新会话标题
    const msgCount = db.prepare('SELECT COUNT(*) as n FROM chat_messages WHERE session_id = ?').get(sid) as { n: number }
    if (msgCount.n === 1) {
      db.prepare('UPDATE chat_sessions SET title = ? WHERE id = ?').run(content.slice(0, 40), sid)
    }

    // 更新模式
    const useMode = mode || session.mode || 'normal'
    if (useMode !== session.mode) {
      db.prepare('UPDATE chat_sessions SET mode = ? WHERE id = ?').run(useMode, sid)
    }

    // 加载历史
    const history = db.prepare(`
      SELECT role, content FROM chat_messages
      WHERE session_id = ? ORDER BY created_at ASC
    `).all(sid) as { role: 'user' | 'assistant'; content: string }[]
    // 排除刚插入的用户消息
    const historyFiltered = history.slice(0, -1)

    send({ type: 'status', data: { status: '正在检索知识库...' } })

    let answer = ''
    let citations: Citation[] = []

    if (useMode === 'agent') {
      // Agent 模式
      const result = await runAgentWorkflow(
        session.kb_id,
        content,
        historyFiltered,
        send,
        { topK },
      )
      answer = result.answer
      citations = result.citations
    } else {
      // 普通 RAG
      const result = await ragAnswer(
        session.kb_id,
        content,
        historyFiltered,
        (token) => send({ type: 'token', data: { content: token } }),
        { topK, mode: 'normal' },
      )
      answer = result.answer
      citations = result.citations
      send({ type: 'citation', data: { citations } })
    }

    // 保存助手消息
    const assistantMsgId = uuid()
    db.prepare(`
      INSERT INTO chat_messages (id, session_id, role, content, citations) VALUES (?, ?, 'assistant', ?, ?)
    `).run(assistantMsgId, sid, answer, JSON.stringify(citations))

    send({ type: 'done', data: {} })
  } catch (err) {
    console.error('Chat error:', err)
    send({ type: 'error', data: { error: (err as Error).message } })
  } finally {
    res.end()
  }
})

export default router

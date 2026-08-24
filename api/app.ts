/**
 * NexusRAG 后端入口
 */
import express, {
  type Request,
  type Response,
  type NextFunction,
} from 'express'
import cors from 'cors'
import helmet from 'helmet'
import rateLimit from 'express-rate-limit'
import path from 'path'
import dotenv from 'dotenv'

import authRoutes from './routes/auth.js'
import kbRoutes from './routes/kb.js'
import documentRoutes from './routes/documents.js'
import chatRoutes from './routes/chat.js'
import { config } from './config.js'

// load env
dotenv.config()

const app: express.Application = express()

// 安全加固：helmet 设置安全响应头
app.use(helmet())

// CORS 白名单（逗号分隔多个源）
app.use(cors({
  origin: (process.env.CORS_ORIGINS || 'http://localhost:5173').split(','),
}))

// 速率限制：每个 IP 每 15 分钟最多 300 次请求
app.use('/api', rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 300,
  standardHeaders: true,
  legacyHeaders: false,
  message: { success: false, error: '请求过于频繁，请稍后再试' },
}))

app.use(express.json({ limit: '10mb' }))
app.use(express.urlencoded({ extended: true, limit: '10mb' }))

// 静态资源（上传的文件等）
app.use('/uploads', express.static(path.resolve(config.storage.uploadPath)))

/**
 * API 路由
 */
app.use('/api/auth', authRoutes)
app.use('/api/kb', kbRoutes)
app.use('/api/kb/:kbId/documents', documentRoutes)
app.use('/api/chat/:kbId', chatRoutes)

/**
 * 健康检查
 */
app.get('/api/health', (_req: Request, res: Response): void => {
  res.json({
    success: true,
    name: 'NexusRAG',
    version: '0.1.0',
    demoMode: config.demoMode,
    llmModel: config.llm.model,
    embeddingDim: config.llm.embeddingDim,
  })
})

/**
 * 错误处理
 */
app.use((error: Error, _req: Request, res: Response, _next: NextFunction): void => {
  console.error('[ERROR]', error)
  res.status(500).json({ success: false, error: error.message || 'Server internal error' })
})

/**
 * 404
 */
app.use((_req: Request, res: Response): void => {
  res.status(404).json({ success: false, error: 'API not found' })
})

export default app

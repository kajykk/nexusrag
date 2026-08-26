/**
 * 本地开发服务器入口
 */
import app from './app.js'
import { config } from './config.js'

const PORT = process.env.PORT || 3001

const server = app.listen(PORT, () => {
  console.log('')
  console.log('  ╔══════════════════════════════════════════════════╗')
  console.log('  ║   NexusRAG 智能知识库 后端服务已启动             ║')
  console.log(`  ║   端口: ${PORT}`)
  console.log(`  ║   模式: ${config.demoMode ? '🎮 Demo (无 LLM)' : '✅ 已配置 LLM'}`)
  if (!config.demoMode) {
    console.log(`  ║   LLM: ${config.llm.model}`)
    console.log(`  ║   Embedding: ${config.llm.embeddingModel}`)
  }
  console.log('  ║                                                  ║')
  console.log('  ╚══════════════════════════════════════════════════╝')
  console.log('')
  if (config.demoMode) {
    console.log('  ⚠️  当前为演示模式，请在 .env 文件配置 OPENAI_API_KEY 以启用真实 LLM')
    console.log('     支持任何兼容 OpenAI 协议的服务（OpenAI / 通义 / DeepSeek / Moonshot 等）')
    console.log('')
  }
  console.log(`  → API:     http://localhost:${PORT}/api`)
  console.log(`  → 健康检查: http://localhost:${PORT}/api/health`)
  console.log('')
})

process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing server...')
  server.close(() => process.exit(0))
})

process.on('SIGINT', () => {
  console.log('\nSIGINT received, closing server...')
  server.close(() => process.exit(0))
})

export default app

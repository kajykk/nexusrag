/**
 * Vitest 全局 setup - 在所有模块导入前设置测试环境变量
 * 确保 db.ts / vectorStore.ts / config.ts 使用隔离的测试路径
 */
import path from 'path'
import fs from 'fs'

const testDir = path.resolve('./data/test')

// 清理上一次测试残留
if (fs.existsSync(testDir)) {
  fs.rmSync(testDir, { recursive: true, force: true })
}
fs.mkdirSync(testDir, { recursive: true })

// 测试专用环境变量（必须在模块导入前设置）
process.env.DB_PATH = path.join(testDir, 'test.db')
process.env.VECTOR_PATH = path.join(testDir, 'vectors')
process.env.UPLOAD_PATH = path.join(testDir, 'uploads')
process.env.JWT_SECRET = 'test-secret-for-vitest'
process.env.OPENAI_API_KEY = ''

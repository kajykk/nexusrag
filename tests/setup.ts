/**
 * Vitest 全局 setup - 在所有模块导入前设置测试环境变量
 * 确保db.ts / vectorStore.ts / config.ts 使用隔离的测试路径
 *
 * 每个 worker 进程使用独立子目录（data/test/w-<pid>）：
 * 并行 worker 不会互相删除对方打开中的 SQLite 文件（Windows 下
 * 共享目录 rmSync 会因句柄占用触发 EPERM）。
 */
import path from 'path'
import fs from 'fs'

const testDir = path.resolve('./data/test')
const workerDir = path.join(testDir, `w-${process.pid}`)

// 清理其它残留 worker 目录（>1 小时），全部容错：失败不影响测试
try {
  if (fs.existsSync(testDir)) {
    const staleMs = 60 * 60 * 1000
    for (const name of fs.readdirSync(testDir)) {
      const dir = path.join(testDir, name)
      if (dir === workerDir) continue
      try {
        if (Date.now() - fs.statSync(dir).mtimeMs > staleMs) {
          fs.rmSync(dir, { recursive: true, force: true })
        }
      } catch { /* 被其它进程占用时跳过 */ }
    }
  }
} catch { /* ignore */ }

fs.mkdirSync(workerDir, { recursive: true })

// 测试专用环境变量（必须在模块导入前设置）
process.env.DB_PATH = path.join(workerDir, 'test.db')
process.env.VECTOR_PATH = path.join(workerDir, 'vectors')
process.env.UPLOAD_PATH = path.join(workerDir, 'uploads')
process.env.JWT_SECRET = 'test-secret-for-vitest'
process.env.OPENAI_API_KEY = ''

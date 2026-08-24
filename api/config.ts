/**
 * 全局配置 - 从环境变量读取，提供默认值
 */
import dotenv from 'dotenv'
dotenv.config()

// JWT 密钥必须在环境变量中配置，禁止使用硬编码默认值
const jwtSecret = process.env.JWT_SECRET
if (!jwtSecret) {
  throw new Error(
    'JWT_SECRET 环境变量未设置。请在 .env 文件中配置 JWT_SECRET（生产环境务必使用强随机值）。',
  )
}

export const config = {
  port: Number(process.env.PORT) || 3001,
  jwtSecret,
  jwtExpiresIn: process.env.JWT_EXPIRES_IN || '7d',

  // LLM 配置（兼容 OpenAI 协议）
  llm: {
    apiKey: process.env.OPENAI_API_KEY || process.env.LLM_API_KEY || '',
    baseURL: process.env.OPENAI_BASE_URL || process.env.LLM_BASE_URL || 'https://api.openai.com/v1',
    model: process.env.LLM_MODEL || 'gpt-4o-mini',
    embeddingModel: process.env.EMBEDDING_MODEL || 'text-embedding-3-small',
    embeddingDim: Number(process.env.EMBEDDING_DIM) || 1536,
  },

  // 数据存储路径
  storage: {
    dbPath: process.env.DB_PATH || './data/nexus.db',
    vectorPath: process.env.VECTOR_PATH || './data/vectors',
    uploadPath: process.env.UPLOAD_PATH || './data/uploads',
  },

  // RAG 参数
  rag: {
    chunkSize: Number(process.env.CHUNK_SIZE) || 500,
    chunkOverlap: Number(process.env.CHUNK_OVERLAP) || 80,
    topK: Number(process.env.TOP_K) || 6,
    rrfK: Number(process.env.RRF_K) || 60,
  },

  // 是否为演示模式（无 API Key 时使用 mock 响应）
  demoMode: !process.env.OPENAI_API_KEY && !process.env.LLM_API_KEY,
}

export type Config = typeof config

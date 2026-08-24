/**
 * LLM 客户端 - 封装 OpenAI 兼容协议的调用
 * 支持流式输出、Embedding、Chat Completion
 * 无 API Key 时启用 Demo 模式（mock 响应）
 */
import OpenAI from 'openai'
import { config } from '../config.js'

const client = new OpenAI({
  apiKey: config.llm.apiKey || 'demo',
  baseURL: config.llm.baseURL,
})

/**
 * 生成 Embedding 向量
 */
export async function embed(text: string): Promise<number[]> {
  if (config.demoMode) {
    // Demo 模式：基于文本哈希生成伪向量（仅供开发测试）
    return mockEmbed(text, config.llm.embeddingDim)
  }
  const res = await client.embeddings.create({
    model: config.llm.embeddingModel,
    input: text,
  })
  return res.data[0].embedding
}

/**
 * 批量生成 Embedding
 */
export async function embedBatch(texts: string[]): Promise<number[][]> {
  if (config.demoMode) {
    return texts.map((t) => mockEmbed(t, config.llm.embeddingDim))
  }
  const res = await client.embeddings.create({
    model: config.llm.embeddingModel,
    input: texts,
  })
  return res.data.map((d) => d.embedding)
}

/**
 * 流式 Chat Completion
 * @param onToken 收到 token 时的回调
 */
export async function chatStream(
  messages: { role: 'system' | 'user' | 'assistant'; content: string }[],
  onToken: (token: string) => void,
  options?: { temperature?: number; maxTokens?: number },
): Promise<string> {
  if (config.demoMode) {
    // Demo 模式：模拟流式输出
    const mockAnswer = generateMockAnswer(messages)
    for (const char of mockAnswer) {
      await new Promise((r) => setTimeout(r, 15))
      onToken(char)
    }
    return mockAnswer
  }

  const stream = await client.chat.completions.create({
    model: config.llm.model,
    messages,
    temperature: options?.temperature ?? 0.3,
    max_tokens: options?.maxTokens,
    stream: true,
  })

  let full = ''
  for await (const chunk of stream) {
    const token = chunk.choices[0]?.delta?.content || ''
    if (token) {
      full += token
      onToken(token)
    }
  }
  return full
}

/**
 * 非流式 Chat Completion
 */
export async function chat(
  messages: { role: 'system' | 'user' | 'assistant'; content: string }[],
  options?: { temperature?: number; maxTokens?: number; json?: boolean },
): Promise<string> {
  if (config.demoMode) {
    return generateMockAnswer(messages)
  }

  const res = await client.chat.completions.create({
    model: config.llm.model,
    messages,
    temperature: options?.temperature ?? 0.3,
    max_tokens: options?.maxTokens,
    response_format: options?.json ? { type: 'json_object' } : undefined,
  })

  return res.choices[0]?.message?.content || ''
}

// ============== Demo 模式辅助函数 ==============

function mockEmbed(text: string, dim: number): number[] {
  // 简单的哈希伪随机向量，确保相同输入得到相同输出
  const vec = new Array(dim)
  let seed = 0
  for (let i = 0; i < text.length; i++) {
    seed = (seed * 31 + text.charCodeAt(i)) | 0
  }
  for (let i = 0; i < dim; i++) {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff
    vec[i] = (seed / 0x7fffffff) * 2 - 1
  }
  // 归一化
  const norm = Math.sqrt(vec.reduce((s, v) => s + v * v, 0))
  return vec.map((v) => v / (norm || 1))
}

function generateMockAnswer(messages: { role: string; content: string }[]): string {
  const userMsg = messages.filter((m) => m.role === 'user').pop()?.content || ''
  return `## 演示模式响应

> ⚠️ 当前未配置 OpenAI API Key，以下为模拟响应。请在项目根目录创建 \`.env\` 文件配置 \`OPENAI_API_KEY\` 后体验真实效果。

**你的问题**：${userMsg.slice(0, 200)}

**模拟回答**：

这是一个基于检索增强生成（RAG）的演示响应。在配置真实 LLM API Key 后，系统会：

1. 通过「向量 + BM25」混合检索从知识库中召回相关片段 [1]
2. 使用 RRF 算法融合多路检索结果 [2]
3. 调用 LLM 基于检索到的上下文生成回答 [1][2]
4. 在回答中标注引用来源，可点击查看原文

**引用说明**：
- [1] 来自示例文档片段一
- [2] 来自示例文档片段二

如需体验完整功能，请在 \`.env\` 中配置：

\`\`\`bash
OPENAI_API_KEY=sk-xxx
# 可选：使用兼容服务（如通义、DeepSeek）
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIM=1024
\`\`\`
`
}

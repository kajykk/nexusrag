/**
 * BM25 关键词检索器 - 简化实现，基于 TF-IDF 思想
 * 支持中英文混合，使用 bigram 处理中文
 */
import db from '../db.js'

// 简单的停用词表
const STOP_WORDS = new Set([
  '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
  '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
  'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
  'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
  'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
  'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
])

/**
 * 分词 - 中英文混合
 */
export function tokenize(text: string): string[] {
  const tokens: string[] = []
  // 英文单词
  const enMatches = text.toLowerCase().match(/[a-z][a-z0-9_-]+/g) || []
  tokens.push(...enMatches.filter((t) => !STOP_WORDS.has(t) && t.length > 1))
  // 中文 bigram
  const cjkMatches = text.match(/[\u4e00-\u9fa5]+/g) || []
  for (const seg of cjkMatches) {
    for (let i = 0; i < seg.length - 1; i++) {
      const bi = seg.slice(i, i + 2)
      if (!STOP_WORDS.has(bi)) tokens.push(bi)
    }
  }
  return tokens
}

interface BM25Doc {
  chunkId: string
  docId: string
  kbId: string
  tokens: string[]
  length: number
}

const docCache = new Map<string, BM25Doc[]>()  // kbId -> docs

/**
 * 加载知识库所有 chunk 到内存索引
 */
export function loadIndex(kbId: string): BM25Doc[] {
  if (docCache.has(kbId)) return docCache.get(kbId)!

  const rows = db.prepare(`
    SELECT c.id as chunk_id, c.doc_id, c.kb_id, c.content
    FROM chunks c
    WHERE c.kb_id = ?
  `).all(kbId) as { chunk_id: string; doc_id: string; kb_id: string; content: string }[]

  const docs: BM25Doc[] = rows.map((r) => ({
    chunkId: r.chunk_id,
    docId: r.doc_id,
    kbId: r.kb_id,
    tokens: tokenize(r.content),
    length: r.content.length,
  }))

  docCache.set(kbId, docs)
  return docs
}

/**
 * 添加文档到 BM25 索引
 */
export function addToIndex(chunkId: string, docId: string, kbId: string, content: string): void {
  const docs = loadIndex(kbId)
  docs.push({
    chunkId,
    docId,
    kbId,
    tokens: tokenize(content),
    length: content.length,
  })
}

/**
 * 删除文档对应的索引
 */
export function removeFromIndex(kbId: string, docId: string): void {
  const docs = loadIndex(kbId)
  const filtered = docs.filter((d) => d.docId !== docId)
  docCache.set(kbId, filtered)
}

/**
 * BM25 检索
 */
export function search(
  kbId: string,
  query: string,
  topK: number = 20,
): { chunkId: string; docId: string; score: number }[] {
  const docs = loadIndex(kbId)
  if (docs.length === 0) return []

  const queryTokens = tokenize(query)
  if (queryTokens.length === 0) return []

  const N = docs.length
  const avgdl = docs.reduce((s, d) => s + d.length, 0) / (N || 1)

  // 计算每个 token 的文档频率
  const df = new Map<string, number>()
  for (const doc of docs) {
    const seen = new Set(doc.tokens)
    for (const t of seen) {
      df.set(t, (df.get(t) || 0) + 1)
    }
  }

  // IDF
  const idf = new Map<string, number>()
  for (const [token, freq] of df) {
    idf.set(token, Math.log((N - freq + 0.5) / (freq + 0.5) + 1))
  }

  // BM25 参数
  const k1 = 1.5
  const b = 0.75

  const scores = docs.map((doc) => {
    let score = 0
    const tf = new Map<string, number>()
    for (const t of doc.tokens) {
      tf.set(t, (tf.get(t) || 0) + 1)
    }
    for (const qt of queryTokens) {
      const f = tf.get(qt) || 0
      if (f === 0) continue
      const idfVal = idf.get(qt) || 0
      const norm = (f * (k1 + 1)) / (f + k1 * (1 - b + b * (doc.length / avgdl)))
      score += idfVal * norm
    }
    return { chunkId: doc.chunkId, docId: doc.docId, score }
  })

  return scores
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, topK)
}

/**
 * 清空缓存（文档变更后调用）
 */
export function clearCache(kbId?: string): void {
  if (kbId) {
    docCache.delete(kbId)
  } else {
    docCache.clear()
  }
}

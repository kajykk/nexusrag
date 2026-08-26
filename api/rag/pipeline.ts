/**
 * RAG Pipeline 核心 - 编排检索 + Rerank + 引用聚合
 */
import db from '../db.js'
import { config } from '../config.js'
import { embed, embedBatch, chatStream } from '../llm/client.js'
import * as vectorStore from './vectorStore.js'
import * as bm25 from './bm25.js'
import { chunkRecursive } from './chunker.js'
import { parseFile } from './parser.js'
import type { Chunk, Citation, RetrievedChunk, Document } from '../types/index.js'

/**
 * 处理上传文档：解析 → 分块 → 向量化 → 入库
 */
export async function ingestDocument(
  kbId: string,
  docId: string,
  filePath: string,
  _fileType: string,
): Promise<{ chunkCount: number }> {
  // 1. 解析文档
  const sections = await parseFile(filePath)

  // 2. 分块
  const chunks = chunkRecursive(
    sections.map((s) => ({ content: s.content, page: s.page, section: s.section })),
    docId,
  )

  if (chunks.length === 0) {
    // 更新状态为 ready 但无内容
    db.prepare(`UPDATE documents SET status = 'ready', chunk_count = 0 WHERE id = ?`).run(docId)
    return { chunkCount: 0 }
  }

  // 3. 批量 Embedding
  const vectors = await embedBatch(chunks.map((c) => c.content))

  // 4. 计算向量库当前基数，使 DB 中 vector_id 与向量库实际位置一致
  //    （事件循环内 count → 事务 → addVectors 之间无 await，单线程下无竞态）
  const vectorIdBase = vectorStore.count(kbId)

  // 5. 写入 SQLite（含 BM25 索引增量更新）
  const insertChunk = db.prepare(`
    INSERT INTO chunks (id, doc_id, kb_id, chunk_index, content, vector_id, token_count, metadata)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `)
  const tx = db.transaction(() => {
    for (let i = 0; i < chunks.length; i++) {
      const c = chunks[i]
      const vectorId = `vec_${vectorIdBase + i}`
      insertChunk.run(
        c.id, c.doc_id, kbId, c.chunk_index, c.content, vectorId, c.token_count,
        c.metadata ? JSON.stringify(c.metadata) : null,
      )
      // 同步更新 BM25 索引
      bm25.addToIndex(c.id, c.doc_id, kbId, c.content)
    }
  })
  tx()

  // 6. 写入向量库（分配的 id 与上面写入 DB 的 vector_id 一致）
  vectorStore.addVectors(
    kbId,
    chunks.map((c, i) => ({ chunkId: c.id, vector: vectors[i] })),
  )
  await vectorStore.persist(kbId)

  // 7. 更新文档状态
  db.prepare(`
    UPDATE documents SET status = 'ready', chunk_count = ? WHERE id = ?
  `).run(chunks.length, docId)

  return { chunkCount: chunks.length }
}

/**
 * 混合检索 - 向量 + BM25 + RRF 融合
 */
export async function retrieve(
  kbId: string,
  query: string,
  topK: number = config.rag.topK,
): Promise<RetrievedChunk[]> {
  // 1. 向量化查询后执行双路检索（均为内存内同步计算）
  const queryVec = await embed(query)

  const vecResults = vectorStore.search(kbId, queryVec, topK * 3)
  const bm25Results = bm25.search(kbId, query, topK * 3)

  // 2. RRF 融合
  const rrfK = config.rag.rrfK
  const rrfScores = new Map<string, { score: number; vectorScore?: number; bm25Score?: number }>()

  for (let i = 0; i < vecResults.length; i++) {
    const r = vecResults[i]
    const rrf = 1 / (rrfK + i + 1)
    const existing = rrfScores.get(r.chunkId) || { score: 0 }
    existing.score += rrf
    existing.vectorScore = r.score
    rrfScores.set(r.chunkId, existing)
  }

  for (let i = 0; i < bm25Results.length; i++) {
    const r = bm25Results[i]
    const rrf = 1 / (rrfK + i + 1)
    const existing = rrfScores.get(r.chunkId) || { score: 0 }
    existing.score += rrf
    existing.bm25Score = r.score
    rrfScores.set(r.chunkId, existing)
  }

  // 3. 按 RRF 排序，取 top K
  const sortedIds = [...rrfScores.entries()]
    .sort((a, b) => b[1].score - a[1].score)
    .slice(0, topK)
    .map(([id]) => id)

  if (sortedIds.length === 0) return []

  // 4. 查询 chunk + doc 详情
  const placeholders = sortedIds.map(() => '?').join(',')
  const rows = db.prepare(`
    SELECT c.id, c.doc_id, c.chunk_index, c.content, c.vector_id, c.token_count, c.metadata,
           d.name as doc_name, d.file_type
    FROM chunks c
    JOIN documents d ON c.doc_id = d.id
    WHERE c.id IN (${placeholders})
  `).all(...sortedIds) as {
    id: string
    doc_id: string
    chunk_index: number
    content: string
    vector_id: string
    token_count: number
    metadata: string | null
    doc_name: string
    file_type: string
  }[]

  // 保留 RRF 排序
  const chunkMap = new Map(rows.map((r) => [r.id, r]))
  return sortedIds.map((id) => {
    const r = chunkMap.get(id)!
    const rrfInfo = rrfScores.get(id)!
    const metadata = r.metadata ? JSON.parse(r.metadata) : {}
    const chunk: Chunk = {
      id: r.id,
      doc_id: r.doc_id,
      chunk_index: r.chunk_index,
      content: r.content,
      vector_id: r.vector_id,
      token_count: r.token_count,
      metadata,
    }
    const doc: Document = {
      id: r.doc_id,
      kb_id: '',
      name: r.doc_name,
      file_type: r.file_type,
      file_size: 0,
      status: 'ready',
      chunk_count: 0,
      created_at: '',
    }
    return {
      chunk,
      doc,
      score: rrfInfo.score,
      vectorScore: rrfInfo.vectorScore,
      bm25Score: rrfInfo.bm25Score,
    }
  })
}

/**
 * 简单 Rerank - 基于关键词重叠度
 * 使用 BM25 的 tokenize（中英文混合），保证中文查询的重叠度可计算
 * （真实场景应使用 Cohere Rerank 或 BGE Reranker，这里用启发式）
 */
export function rerank(query: string, results: RetrievedChunk[]): RetrievedChunk[] {
  const queryTokens = new Set(bm25.tokenize(query))
  return results
    .map((r) => {
      const contentTokens = new Set(bm25.tokenize(r.chunk.content))
      const overlap = [...queryTokens].filter((t) => contentTokens.has(t)).length
      const overlapScore = overlap / (queryTokens.size || 1)
      return {
        ...r,
        score: r.score * 0.7 + overlapScore * 0.3,
      }
    })
    .sort((a, b) => b.score - a.score)
}

/**
 * 将检索结果转为引用格式
 */
export function toCitations(results: RetrievedChunk[]): Citation[] {
  return results.map((r, i) => ({
    id: i + 1,
    docId: r.doc.id,
    docName: r.doc.name,
    content: r.chunk.content.slice(0, 500),
    page: r.chunk.metadata?.page,
    score: r.score,
  }))
}

/**
 * 普通 RAG 问答
 */
export async function ragAnswer(
  kbId: string,
  query: string,
  history: { role: 'user' | 'assistant'; content: string }[],
  onToken: (token: string) => void,
  options?: { topK?: number; mode?: 'normal' | 'agent' },
): Promise<{ answer: string; citations: Citation[] }> {
  // 1. 检索
  const topK = options?.topK || config.rag.topK
  let results = await retrieve(kbId, query, topK)
  // 2. Rerank
  results = rerank(query, results)
  // 3. 引用
  const citations = toCitations(results)

  // 4. 构造 Prompt
  const context = results
    .map((r, i) => `[${i + 1}] (来源: ${r.doc.name})\n${r.chunk.content}`)
    .join('\n\n---\n\n')

  const systemPrompt = `你是 NexusRAG 智能知识库助手。基于以下检索到的上下文回答用户问题。

要求：
1. 答案必须基于提供的上下文，不得编造
2. 引用上下文时使用 [1][2] 这样的标注，数字对应引用编号
3. 如果上下文不足以回答，明确说明"根据当前知识库，无法完整回答此问题"
4. 答案使用 Markdown 格式，含代码块、列表等
5. 回答简洁、专业、有条理

## 检索到的上下文

${context || '（未检索到相关内容）'}

## 引用列表

${citations.map((c) => `[${c.id}] ${c.docName} - ${c.content.slice(0, 80)}...`).join('\n')}
`

  const messages: { role: 'system' | 'user' | 'assistant'; content: string }[] = [
    { role: 'system', content: systemPrompt },
    ...history.slice(-6).map((h) => ({ role: h.role, content: h.content })),
    { role: 'user', content: query },
  ]

  // 5. 流式生成
  const answer = await chatStream(messages, onToken, { temperature: 0.3 })

  return { answer, citations }
}

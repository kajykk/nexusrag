/**
 * 纯 JS 向量存储 - 线性 cosine 相似度检索
 * 数据持久化为 JSON 文件，每个知识库一个索引
 *
 * 对于演示规模（<10k 向量）线性检索足够快
 */
import fs from 'fs'
import path from 'path'
import { config } from '../config.js'

interface IndexEntry {
  chunkIds: string[]
  vectors: number[][]  // [chunk_id_idx][dim]
  dirty: boolean
}

const vecDir = config.storage.vectorPath
if (!fs.existsSync(vecDir)) {
  fs.mkdirSync(vecDir, { recursive: true })
}

const indexCache = new Map<string, IndexEntry>()

function indexPath(kbId: string): string {
  return path.join(vecDir, `${kbId}.json`)
}

/**
 * 获取或创建知识库的向量索引
 */
export function getIndex(kbId: string): IndexEntry {
  if (indexCache.has(kbId)) {
    return indexCache.get(kbId)!
  }

  const file = indexPath(kbId)
  let entry: IndexEntry

  if (fs.existsSync(file)) {
    const data = JSON.parse(fs.readFileSync(file, 'utf-8'))
    entry = {
      chunkIds: data.chunkIds,
      vectors: data.vectors,
      dirty: false,
    }
  } else {
    entry = { chunkIds: [], vectors: [], dirty: false }
  }

  indexCache.set(kbId, entry)
  return entry
}

/**
 * 添加单个向量
 */
export function addVector(kbId: string, chunkId: string, vector: number[]): string {
  const entry = getIndex(kbId)
  const id = entry.chunkIds.length
  entry.chunkIds.push(chunkId)
  entry.vectors.push(vector)
  entry.dirty = true
  return `vec_${id}`
}

/**
 * 批量添加向量
 */
export function addVectors(kbId: string, items: { chunkId: string; vector: number[] }[]): string[] {
  const entry = getIndex(kbId)
  const ids: string[] = []
  for (const item of items) {
    const id = entry.chunkIds.length
    entry.chunkIds.push(item.chunkId)
    entry.vectors.push(item.vector)
    ids.push(`vec_${id}`)
  }
  entry.dirty = true
  return ids
}

/**
 * Cosine 相似度
 */
export function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0
  let normA = 0
  let normB = 0
  const len = Math.min(a.length, b.length)
  for (let i = 0; i < len; i++) {
    dot += a[i] * b[i]
    normA += a[i] * a[i]
    normB += b[i] * b[i]
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB)
  return denom === 0 ? 0 : dot / denom
}

/**
 * 向量检索 - 线性扫描
 */
export function search(
  kbId: string,
  queryVec: number[],
  topK: number,
): { chunkId: string; score: number }[] {
  const entry = getIndex(kbId)
  if (entry.chunkIds.length === 0) return []

  const scores: { chunkId: string; score: number }[] = []
  for (let i = 0; i < entry.chunkIds.length; i++) {
    const score = cosineSimilarity(queryVec, entry.vectors[i])
    scores.push({ chunkId: entry.chunkIds[i], score })
  }

  return scores
    .sort((a, b) => b.score - a.score)
    .slice(0, Math.min(topK, scores.length))
}

/**
 * 持久化索引到磁盘
 */
export function persist(kbId: string): void {
  const entry = indexCache.get(kbId)
  if (!entry || !entry.dirty) return
  fs.writeFileSync(
    indexPath(kbId),
    JSON.stringify({
      chunkIds: entry.chunkIds,
      vectors: entry.vectors,
    }),
  )
  entry.dirty = false
}

/**
 * 删除知识库的向量索引
 */
export function deleteIndex(kbId: string): void {
  indexCache.delete(kbId)
  const f = indexPath(kbId)
  if (fs.existsSync(f)) fs.unlinkSync(f)
}

/**
 * 删除文档对应的所有向量
 */
export function removeByDoc(kbId: string, _docId: string, chunkIds: string[]): void {
  const entry = getIndex(kbId)
  const chunkIdSet = new Set(chunkIds)
  const newChunkIds: string[] = []
  const newVectors: number[][] = []
  for (let i = 0; i < entry.chunkIds.length; i++) {
    if (!chunkIdSet.has(entry.chunkIds[i])) {
      newChunkIds.push(entry.chunkIds[i])
      newVectors.push(entry.vectors[i])
    }
  }
  entry.chunkIds = newChunkIds
  entry.vectors = newVectors
  entry.dirty = true
  persist(kbId)
}

/**
 * 获取索引中的向量数量
 */
export function count(kbId: string): number {
  return getIndex(kbId).chunkIds.length
}

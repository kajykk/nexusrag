/**
 * 纯 JS 向量存储 - 线性 cosine 相似度检索
 *
 * 持久化格式：
 *   - 二进制格式（默认）：`NXVEC1` 魔数 + chunkIds JSON 头 + Float32Array 向量区，
 *     序列化/反序列化开销与体积远小于 JSON
 *   - 兼容旧 JSON 格式：读取时按文件头自动识别
 *
 * 写入策略：异步原子写（先写临时文件再 rename），persist 不阻塞事件循环
 *
 * 对于演示规模（<10k 向量）线性检索足够快
 */
import fs from 'fs'
import fsp from 'fs/promises'
import path from 'path'
import { config } from '../config.js'

const MAGIC = 'NXVEC1'

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

/** 进行中的持久化任务，避免同一索引并发写盘 */
const pendingWrites = new Map<string, Promise<void>>()

function indexPath(kbId: string): string {
  return path.join(vecDir, `${kbId}.json`)
}

function parseBinary(buf: Buffer): { chunkIds: string[]; vectors: number[][] } | null {
  const magicLen = Buffer.byteLength(MAGIC, 'utf-8')
  if (buf.length < magicLen + 4 || buf.subarray(0, magicLen).toString('utf-8') !== MAGIC) {
    return null
  }
  let offset = magicLen
  const headerLen = buf.readUInt32LE(offset)
  offset += 4
  const header = JSON.parse(buf.subarray(offset, offset + headerLen).toString('utf-8')) as {
    chunkIds: string[]
    dim: number
  }
  offset += headerLen

  const { chunkIds, dim } = header
  const n = chunkIds.length
  const floats = new Float32Array(
    buf.buffer.slice(buf.byteOffset + offset, buf.byteOffset + offset + n * dim * 4),
  )
  const vectors: number[][] = []
  for (let i = 0; i < n; i++) {
    vectors.push(Array.from(floats.subarray(i * dim, (i + 1) * dim)))
  }
  return { chunkIds, vectors }
}

function serializeBinary(entry: IndexEntry): Buffer {
  // 以最大维度为准，短向量右侧补零，保证向量区等长可寻址
  const dim = entry.vectors.reduce((m, v) => Math.max(m, v.length), 0)
  const padded: number[][] = entry.vectors.map((v) => (v.length === dim ? v : [...v, ...new Array(dim - v.length).fill(0)]))

  const header = JSON.stringify({ chunkIds: entry.chunkIds, dim })
  const headerBuf = Buffer.from(header, 'utf-8')
  const floats = new Float32Array(entry.chunkIds.length * dim)
  for (let i = 0; i < padded.length; i++) {
    floats.set(padded[i], i * dim)
  }
  const vecBuf = Buffer.from(floats.buffer)

  return Buffer.concat([
    Buffer.from(MAGIC, 'utf-8'),
    (() => {
      const b = Buffer.alloc(4)
      b.writeUInt32LE(headerBuf.length, 0)
      return b
    })(),
    headerBuf,
    vecBuf,
  ])
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
    const buf = fs.readFileSync(file)
    const binary = parseBinary(buf)
    if (binary) {
      entry = { chunkIds: binary.chunkIds, vectors: binary.vectors, dirty: false }
    } else {
      // 兼容旧 JSON 格式
      const data = JSON.parse(buf.toString('utf-8'))
      entry = {
        chunkIds: data.chunkIds,
        vectors: data.vectors,
        dirty: false,
      }
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
 * 持久化索引到磁盘 - 异步原子写（临时文件 + rename）
 *
 * 返回 Promise；同一索引重复调用会串行执行，不会并发写同一文件。
 * 注意：调用方需自行 await 或容忍进程退出时最后一次写入丢失。
 */
export function persist(kbId: string): Promise<void> {
  const entry = indexCache.get(kbId)
  if (!entry || !entry.dirty) return Promise.resolve()

  const prev = pendingWrites.get(kbId) ?? Promise.resolve()
  const task = prev
    .then(async () => {
      if (!indexCache.has(kbId) || !entry.dirty) return
      const file = indexPath(kbId)
      const tmpFile = `${file}.${process.pid}.${Date.now()}.tmp`
      await fsp.writeFile(tmpFile, serializeBinary(entry))
      await fsp.rename(tmpFile, file)  // rename 原子替换，避免写一半崩溃导致索引损坏
      entry.dirty = false
    })
    .catch((err) => {
      console.error(`[vectorStore] persist ${kbId} failed:`, err)
    })
    .finally(() => {
      if (pendingWrites.get(kbId) === task) pendingWrites.delete(kbId)
    })

  pendingWrites.set(kbId, task)
  return task
}

/**
 * 删除知识库的向量索引
 */
export function deleteIndex(kbId: string): void {
  indexCache.delete(kbId)
  pendingWrites.delete(kbId)
  const f = indexPath(kbId)
  if (fs.existsSync(f)) fs.unlinkSync(f)
}

/**
 * 删除文档对应的所有向量
 */
export async function removeByDoc(kbId: string, _docId: string, chunkIds: string[]): Promise<void> {
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
  await persist(kbId)
}

/**
 * 获取索引中的向量数量
 */
export function count(kbId: string): number {
  return getIndex(kbId).chunkIds.length
}

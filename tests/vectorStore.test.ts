/**
 * 向量存储单元测试
 */
import { describe, it, expect, beforeEach } from 'vitest'
import {
  cosineSimilarity,
  addVectors,
  search,
  deleteIndex,
  getIndex,
  count,
} from '../api/rag/vectorStore.js'

describe('cosineSimilarity', () => {
  it('完全相同的向量相似度为 1', () => {
    const v = [1, 2, 3]
    expect(cosineSimilarity(v, v)).toBeCloseTo(1, 10)
  })

  it('正交向量相似度为 0', () => {
    expect(cosineSimilarity([1, 0], [0, 1])).toBeCloseTo(0, 10)
  })

  it('相反方向向量相似度为 -1', () => {
    expect(cosineSimilarity([1, 0], [-1, 0])).toBeCloseTo(-1, 10)
  })

  it('长度不同的向量取较短的维度计算', () => {
    // [1,0] vs [1,0,999] → 前两维相同，相似度 1
    expect(cosineSimilarity([1, 0], [1, 0, 999])).toBeCloseTo(1, 10)
  })

  it('零向量相似度为 0（避免除以 0）', () => {
    expect(cosineSimilarity([0, 0, 0], [1, 2, 3])).toBe(0)
  })
})

describe('vectorStore search', () => {
  const kbId = 'test-kb-vec'

  beforeEach(() => {
    deleteIndex(kbId)
  })

  it('空索引返回空结果', () => {
    const results = search(kbId, [1, 2, 3], 5)
    expect(results).toEqual([])
  })

  it('能按相似度排序返回 topK 结果', () => {
    addVectors(kbId, [
      { chunkId: 'chunk-a', vector: [1, 0, 0] },
      { chunkId: 'chunk-b', vector: [0.9, 0.1, 0] },
      { chunkId: 'chunk-c', vector: [0, 1, 0] },
    ])
    const results = search(kbId, [1, 0, 0], 3)
    expect(results.length).toBe(3)
    // 最相似的应排在最前
    expect(results[0].chunkId).toBe('chunk-a')
    expect(results[0].score).toBeCloseTo(1, 10)
  })

  it('topK 限制返回数量', () => {
    addVectors(kbId, [
      { chunkId: 'a', vector: [1, 0] },
      { chunkId: 'b', vector: [0.8, 0.2] },
      { chunkId: 'c', vector: [0.6, 0.4] },
      { chunkId: 'd', vector: [0, 1] },
    ])
    const results = search(kbId, [1, 0], 2)
    expect(results.length).toBe(2)
  })

  it('addVectors 后 count 正确递增', () => {
    expect(count(kbId)).toBe(0)
    addVectors(kbId, [
      { chunkId: 'x', vector: [1, 2] },
      { chunkId: 'y', vector: [3, 4] },
    ])
    expect(count(kbId)).toBe(2)
    expect(getIndex(kbId).chunkIds).toContain('x')
    expect(getIndex(kbId).chunkIds).toContain('y')
  })
})

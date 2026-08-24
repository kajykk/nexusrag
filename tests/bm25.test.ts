/**
 * BM25 检索器单元测试
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { tokenize, addToIndex, search, clearCache } from '../api/rag/bm25.js'

describe('tokenize', () => {
  it('英文单词分词（小写化、过滤停用词）', () => {
    const tokens = tokenize('The quick brown fox jumps over the lazy dog')
    expect(tokens).toContain('quick')
    expect(tokens).toContain('brown')
    expect(tokens).toContain('fox')
    expect(tokens).toContain('lazy')
    expect(tokens).toContain('dog')
    // 停用词 'the' 应被过滤
    expect(tokens).not.toContain('the')
  })

  it('中文 bigram 分词', () => {
    const tokens = tokenize('自然语言处理')
    expect(tokens).toContain('自然')
    expect(tokens).toContain('然语')
    expect(tokens).toContain('语言')
    expect(tokens).toContain('言处')
    expect(tokens).toContain('处理')
  })

  it('中英文混合分词', () => {
    const tokens = tokenize('RAG 检索增强生成')
    expect(tokens).toContain('rag')
    expect(tokens).toContain('检索')
    expect(tokens).toContain('增强')
    expect(tokens).toContain('生成')
  })

  it('过滤单字符英文（长度 <= 1）', () => {
    const tokens = tokenize('a b c dd ee')
    expect(tokens).not.toContain('a')
    expect(tokens).not.toContain('b')
    expect(tokens).toContain('dd')
    expect(tokens).toContain('ee')
  })

  it('空字符串返回空数组', () => {
    expect(tokenize('')).toEqual([])
  })
})

describe('BM25 search', () => {
  const kbId = 'test-kb-bm25'

  beforeEach(() => {
    clearCache(kbId)
  })

  it('能检索到包含查询词的文档', () => {
    addToIndex('chunk-1', 'doc-1', kbId, '机器学习是人工智能的一个分支')
    addToIndex('chunk-2', 'doc-1', kbId, '深度学习使用神经网络')

    const results = search(kbId, '机器学习', 10)
    expect(results.length).toBeGreaterThan(0)
    // 包含查询词的文档应排在前面
    expect(results[0].chunkId).toBe('chunk-1')
  })

  it('不包含查询词的文档不出现在结果中', () => {
    addToIndex('chunk-a', 'doc-1', kbId, '今天天气很好')
    addToIndex('chunk-b', 'doc-1', kbId, '数据库管理系统')

    const results = search(kbId, '天气', 10)
    expect(results.length).toBe(1)
    expect(results[0].chunkId).toBe('chunk-a')
  })

  it('空查询返回空结果', () => {
    addToIndex('chunk-1', 'doc-1', kbId, 'some content')
    const results = search(kbId, '', 10)
    expect(results).toEqual([])
  })

  it('topK 限制返回数量', () => {
    for (let i = 0; i < 5; i++) {
      addToIndex(`chunk-${i}`, 'doc-1', kbId, `机器学习算法第${i}章`)
    }
    const results = search(kbId, '机器学习', 2)
    expect(results.length).toBe(2)
  })

  it('结果按分数降序排列', () => {
    addToIndex('chunk-low', 'doc-1', kbId, '机器学习基础')
    addToIndex('chunk-high', 'doc-1', kbId, '机器学习 机器学习 机器学习 深度学习')
    const results = search(kbId, '机器学习', 10)
    expect(results.length).toBe(2)
    // 分数应降序
    expect(results[0].score).toBeGreaterThanOrEqual(results[1].score)
    // 出现次数更多的文档分数更高
    expect(results[0].chunkId).toBe('chunk-high')
  })
})

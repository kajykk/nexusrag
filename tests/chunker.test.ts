/**
 * 分块器单元测试
 */
import { describe, it, expect } from 'vitest'
import { chunkRecursive, estimateTokens } from '../api/rag/chunker.js'

describe('chunkRecursive', () => {
  it('短文本生成单个 chunk', () => {
    const chunks = chunkRecursive([{ content: '短文本' }], 'doc-1')
    expect(chunks.length).toBe(1)
    expect(chunks[0].content).toBe('短文本')
    expect(chunks[0].doc_id).toBe('doc-1')
    expect(chunks[0].chunk_index).toBe(0)
  })

  it('chunk 大小不超过指定上限', () => {
    const longText = 'A'.repeat(1000)
    const chunks = chunkRecursive([{ content: longText }], 'doc-1', 100, 20)
    expect(chunks.length).toBeGreaterThan(1)
    for (const chunk of chunks) {
      expect(chunk.content.length).toBeLessThanOrEqual(100)
    }
  })

  it('在段落边界优先合并', () => {
    const text = '第一段内容。\n\n第二段内容。\n\n第三段内容。'
    const chunks = chunkRecursive([{ content: text }], 'doc-1', 500, 50)
    // 整个文本不超过 500 字符，应在单个 chunk 中保留段落结构
    expect(chunks.length).toBe(1)
    expect(chunks[0].content).toContain('第一段内容')
    expect(chunks[0].content).toContain('第二段内容')
    expect(chunks[0].content).toContain('第三段内容')
  })

  it('多段落超长文本分多个 chunk', () => {
    const para1 = 'A'.repeat(300)
    const para2 = 'B'.repeat(300)
    const text = `${para1}\n\n${para2}`
    const chunks = chunkRecursive([{ content: text }], 'doc-1', 500, 50)
    expect(chunks.length).toBe(2)
    expect(chunks[0].content).toContain('A')
    expect(chunks[1].content).toContain('B')
  })

  it('chunk_index 递增', () => {
    const sections = [
      { content: 'A'.repeat(300) },
      { content: 'B'.repeat(300) },
    ]
    const chunks = chunkRecursive(sections, 'doc-1', 200, 50)
    for (let i = 0; i < chunks.length; i++) {
      expect(chunks[i].chunk_index).toBe(i)
    }
  })

  it('保留 section 元信息到 metadata', () => {
    const chunks = chunkRecursive(
      [{ content: '内容', page: 5, section: '引言' }],
      'doc-1',
    )
    expect(chunks[0].metadata?.page).toBe(5)
    expect(chunks[0].metadata?.section).toBe('引言')
  })

  it('空内容被跳过', () => {
    const chunks = chunkRecursive(
      [{ content: '' }, { content: '   ' }, { content: '有效内容' }],
      'doc-1',
    )
    expect(chunks.length).toBe(1)
    expect(chunks[0].content).toBe('有效内容')
  })
})

describe('estimateTokens', () => {
  it('纯中文：1 字 ≈ 1 token', () => {
    expect(estimateTokens('自然语言处理')).toBe(6)
  })

  it('纯英文：4 字符 ≈ 1 token', () => {
    expect(estimateTokens('hello')).toBe(Math.ceil(5 / 4))
  })

  it('中英文混合', () => {
    const text = '你好hello' // 2 中文 + 5 英文
    expect(estimateTokens(text)).toBe(2 + Math.ceil(5 / 4))
  })

  it('空字符串返回 0', () => {
    expect(estimateTokens('')).toBe(0)
  })
})

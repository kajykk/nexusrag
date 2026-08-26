/**
 * Markdown 渲染 composable 单元测试
 */
import { describe, it, expect } from 'vitest'
import { useMarkdown } from '../src/composables/useMarkdown'
import type { Citation } from '../src/api/types'

const citations: Citation[] = [
  { id: 1, docId: 'd1', docName: '文档一', content: '内容片段一', page: 3, score: 0.9 },
  { id: 2, docId: 'd2', docName: '文档二', content: '内容片段二', score: 0.8 },
]

function render(content: string, cites: Citation[] = citations): string {
  const { rendered } = useMarkdown(
    () => content,
    () => cites,
  )
  return rendered.value
}

describe('useMarkdown - 引用标记转换', () => {
  it('[1] 被转换为可点击的引用 span', () => {
    const html = render('根据资料[1]可知')
    expect(html).toContain('class="citation-ref"')
    expect(html).toContain('data-citation=')
    expect(html).not.toContain('根据资料[1]') // 原始标记已被替换
  })

  it('多个连续引用均可转换', () => {
    const html = render('结论[1][2]成立')
    expect((html.match(/citation-ref/g) || []).length).toBe(2)
  })

  it('无匹配引用的编号保持原样', () => {
    const html = render('未知编号[99]')
    expect(html).toContain('[99]')
    expect(html).not.toContain('citation-ref')
  })

  it('不误伤 Markdown 链接语法 [text](url)', () => {
    const html = render('[点这里](https://example.com)')
    expect(html).toContain('<a href="https://example.com">')
    expect(html).not.toContain('citation-ref')
  })
})

describe('useMarkdown - 安全与高亮', () => {
  it('原始 HTML 被转义（html:false）', () => {
    const html = render('<img src=x onerror=alert(1)>')
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img')
  })

  it('已知语言代码块走 highlight.js 渲染', () => {
    const html = render('```python\nprint("hi")\n```')
    expect(html).toContain('hljs')
  })

  it('空内容返回空字符串', () => {
    expect(render('', [])).toBe('')
  })
})

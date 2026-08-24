/**
 * Markdown 渲染 composable - 含代码高亮、引用标记转换
 */
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import type { Citation } from '@/api/types'

// 配置 markdown-it
const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: false,
  highlight(str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang, ignoreIllegals: true }).value}</code></pre>`
      } catch {
        // ignore
      }
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

// 自定义渲染：将 [1] [2] 转换为可点击的引用标记
function renderCitations(text: string, citations: Citation[] = []): string {
  if (!citations.length) return text
  // 匹配 [1] [2][3] 这种模式，但避免匹配 Markdown 链接 [text](url)
  return text.replace(/\[(\d+)\](?!\()/g, (match, numStr) => {
    const num = Number(numStr)
    const c = citations.find((x) => x.id === num)
    if (!c) return match
    const data = encodeURIComponent(JSON.stringify(c))
    return `<span class="citation-ref" data-citation="${data}">${num}</span>`
  })
}

export function useMarkdown(content: () => string, citations: () => Citation[] = () => []) {
  const rendered = computed(() => {
    const raw = content()
    if (!raw) return ''
    const html = md.render(raw)
    return renderCitations(html, citations())
  })
  return { rendered }
}

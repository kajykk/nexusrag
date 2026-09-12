/**
 * Markdown 渲染 composable - 含代码高亮、引用标记转换
 */
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
// 按需注册语言：全量 highlight.js 约占打包体积 1MB，实际只需常见语言
import hljs from 'highlight.js/lib/core'
import javascript from 'highlight.js/lib/languages/javascript'
import typescript from 'highlight.js/lib/languages/typescript'
import python from 'highlight.js/lib/languages/python'
import json from 'highlight.js/lib/languages/json'
import bash from 'highlight.js/lib/languages/bash'
import sql from 'highlight.js/lib/languages/sql'
import xml from 'highlight.js/lib/languages/xml'
import markdownLang from 'highlight.js/lib/languages/markdown'
import type { Citation } from '@/api/types'

for (const [name, lang] of [
  ['javascript', javascript],
  ['typescript', typescript],
  ['python', python],
  ['json', json],
  ['bash', bash],
  ['sql', sql],
  ['xml', xml],
  ['markdown', markdownLang],
] as const) {
  hljs.registerLanguage(name, lang)
}

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
// 只在 DOM 中内联引用 id，完整引用对象由 ChatMarkdown 组件持有，
// 点击时按 id 回查，避免大对象内联在 HTML 中。
function renderCitations(text: string, citations: Citation[] = []): string {
  if (!citations.length) return text
  // 匹配 [1] [2][3] 这种模式，但避免匹配 Markdown 链接 [text](url)
  return text.replace(/\[(\d+)\](?!\()/g, (match, numStr) => {
    const num = Number(numStr)
    const c = citations.find((x) => x.id === num)
    if (!c) return match
    return `<span class="citation-ref" data-citation-id="${num}">${num}</span>`
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

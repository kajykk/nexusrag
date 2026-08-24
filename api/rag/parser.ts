/**
 * 文档解析器 - 支持 PDF / Word / Markdown / 纯文本
 */
import fs from 'fs'
import path from 'path'
import pdfParse from 'pdf-parse'
import mammoth from 'mammoth'
import { marked } from 'marked'

export interface ParsedSection {
  content: string
  page?: number
  section?: string
}

/**
 * 解析文件为文本片段
 */
export async function parseFile(filePath: string): Promise<ParsedSection[]> {
  const ext = path.extname(filePath).toLowerCase()
  switch (ext) {
    case '.pdf':
      return parsePdf(filePath)
    case '.docx':
    case '.doc':
      return parseWord(filePath)
    case '.md':
    case '.markdown':
      return parseMarkdown(filePath)
    case '.txt':
    case '.text':
      return parseText(filePath)
    default:
      // 默认按文本处理
      return parseText(filePath)
  }
}

async function parsePdf(filePath: string): Promise<ParsedSection[]> {
  const buf = fs.readFileSync(filePath)
  const data = await pdfParse(buf)
  // PDF 按页分割（pdf-parse 不直接支持按页，这里按 form feed 切分）
  const pages = data.text.split('\f')
  if (pages.length > 1) {
    return pages
      .map((content, i) => ({ content: content.trim(), page: i + 1 }))
      .filter((s) => s.content.length > 0)
  }
  return [{ content: data.text, page: 1 }]
}

async function parseWord(filePath: string): Promise<ParsedSection[]> {
  const result = await mammoth.extractRawText({ path: filePath })
  return [{ content: result.value, section: 'main' }]
}

async function parseMarkdown(filePath: string): Promise<ParsedSection[]> {
  const raw = fs.readFileSync(filePath, 'utf-8')
  // 按 ## 标题切分
  const sections: ParsedSection[] = []
  const parts = raw.split(/^## /m)
  if (parts.length > 1) {
    for (let i = 1; i < parts.length; i++) {
      const [title, ...rest] = parts[i].split('\n')
      sections.push({
        content: `## ${title}\n${rest.join('\n')}`.trim(),
        section: title.trim(),
      })
    }
    // 第一部分是前言
    if (parts[0].trim()) {
      sections.unshift({ content: parts[0].trim(), section: 'intro' })
    }
  } else {
    sections.push({ content: marked.parse(raw, { async: false }) as string })
  }
  return sections
}

async function parseText(filePath: string): Promise<ParsedSection[]> {
  const content = fs.readFileSync(filePath, 'utf-8')
  return [{ content }]
}

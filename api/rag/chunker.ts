/**
 * 智能分块器 - 支持递归分块、语义分块、表格感知
 */
import { config } from '../config.js'
import type { Chunk } from '../types/index.js'

export interface ChunkInput {
  content: string
  page?: number
  section?: string
}

/**
 * 递归字符分块（保留语义边界）
 */
export function chunkRecursive(
  sections: ChunkInput[],
  docId: string,
  chunkSize: number = config.rag.chunkSize,
  overlap: number = config.rag.chunkOverlap,
): Chunk[] {
  const chunks: Chunk[] = []
  let chunkIndex = 0

  for (const section of sections) {
    const text = section.content
    if (!text || !text.trim()) continue

    // 优先在段落边界切分
    const paragraphs = text.split(/\n\s*\n/)
    let buffer = ''

    for (const para of paragraphs) {
      if ((buffer + '\n\n' + para).length <= chunkSize) {
        buffer = buffer ? buffer + '\n\n' + para : para
      } else {
        if (buffer) {
          chunks.push(createChunk(buffer, docId, chunkIndex++, section))
          buffer = ''
        }
        // 单段超长，进一步切分
        if (para.length > chunkSize) {
          const pieces = splitLongText(para, chunkSize, overlap)
          for (const piece of pieces) {
            chunks.push(createChunk(piece, docId, chunkIndex++, section))
          }
        } else {
          buffer = para
        }
      }
    }
    if (buffer) {
      chunks.push(createChunk(buffer, docId, chunkIndex++, section))
    }
  }

  return chunks
}

function splitLongText(text: string, size: number, overlap: number): string[] {
  const pieces: string[] = []
  let start = 0
  while (start < text.length) {
    let end = start + size
    // 尝试在句号处切分
    if (end < text.length) {
      const sentenceEnd = findSentenceEnd(text, start, end)
      if (sentenceEnd > start + size * 0.5) {
        end = sentenceEnd
      }
    }
    pieces.push(text.slice(start, end).trim())
    start = end - overlap
  }
  return pieces.filter((p) => p.length > 0)
}

function findSentenceEnd(text: string, start: number, end: number): number {
  // 优先级：句号 > 换行 > 空格
  const markers = /[。！？.!?]/g
  let lastMatch = -1
  for (let i = end - 1; i > start; i--) {
    if (markers.test(text[i])) {
      lastMatch = i + 1
      break
    }
  }
  return lastMatch > 0 ? lastMatch : end
}

function createChunk(
  content: string,
  docId: string,
  index: number,
  section: ChunkInput,
): Chunk {
  return {
    id: `${docId}_chunk_${index}`,
    doc_id: docId,
    chunk_index: index,
    content,
    vector_id: '',  // 后续添加向量时填入
    token_count: Math.ceil(content.length / 4),  // 粗略估算
    metadata: {
      page: section.page,
      section: section.section,
    },
  }
}

/**
 * 估算 token 数（粗略：中文 1 字 ≈ 1 token，英文 4 字符 ≈ 1 token）
 */
export function estimateTokens(text: string): number {
  const cjk = (text.match(/[\u4e00-\u9fa5]/g) || []).length
  const other = text.length - cjk
  return cjk + Math.ceil(other / 4)
}

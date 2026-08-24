/**
 * 共享类型定义
 */

export interface User {
  id: string
  email: string
  name: string
  created_at: string
}

export interface KnowledgeBase {
  id: string
  user_id: string
  name: string
  description: string
  document_count: number
  created_at: string
}

export interface Document {
  id: string
  kb_id: string
  name: string
  file_type: string
  file_size: number
  status: 'pending' | 'processing' | 'ready' | 'failed'
  chunk_count: number
  error?: string
  created_at: string
}

export interface Chunk {
  id: string
  doc_id: string
  chunk_index: number
  content: string
  vector_id: string
  token_count: number
  metadata?: {
    page?: number
    section?: string
  }
}

export interface ChatSession {
  id: string
  kb_id: string
  user_id: string
  title: string
  mode: 'normal' | 'agent'
  created_at: string
}

export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  citations?: Citation[]
  created_at: string
}

export interface Citation {
  id: number
  docId: string
  docName: string
  content: string
  page?: number
  score: number
}

export interface ChatRequest {
  content: string
  mode?: 'normal' | 'agent'
  topK?: number
}

export interface RetrievedChunk {
  chunk: Chunk
  doc: Document
  score: number
  vectorScore?: number
  bm25Score?: number
}

export interface StreamChunk {
  type: 'token' | 'citation' | 'status' | 'done' | 'error'
  data: {
    content?: string
    citations?: Citation[]
    status?: string
    error?: string
  }
}

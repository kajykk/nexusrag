import client from './client'
import type { Citation } from './types'


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

export const chatApi = {
  async listSessions(kbId: string): Promise<ChatSession[]> {
    const { data } = await client.get(`/chat/${kbId}/sessions`)
    return data.data
  },
  async createSession(kbId: string, opts: { title?: string; mode?: 'normal' | 'agent' } = {}): Promise<ChatSession> {
    const { data } = await client.post(`/chat/${kbId}/sessions`, opts)
    return data.data
  },
  async deleteSession(kbId: string, sid: string): Promise<void> {
    await client.delete(`/chat/${kbId}/sessions/${sid}`)
  },
  async getMessages(kbId: string, sid: string): Promise<ChatMessage[]> {
    const { data } = await client.get(`/chat/${kbId}/sessions/${sid}/messages`)
    return data.data
  },
  /**
   * 发送消息 - SSE 流式接收
   *
   * 使用 XMLHttpRequest 渐进式读取，兼容所有 webview（含 trae-preview / Electron）。
   * fetch + ReadableStream 在某些 webview 中会被 ERR_ABORTED。
   */
  sendMessage(
    kbId: string,
    sid: string,
    content: string,
    mode: 'normal' | 'agent' = 'normal',
    onChunk: (chunk: {
      type: 'token' | 'citation' | 'status' | 'done' | 'error'
      data: any
    }) => void,
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const token = localStorage.getItem('nexus_token')
      const url = `/api/chat/${kbId}/sessions/${sid}/messages`

      const xhr = new XMLHttpRequest()
      xhr.open('POST', url, true)
      xhr.setRequestHeader('Content-Type', 'application/json')
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      // 关键：禁用 IE 缓存与请求缓冲
      xhr.setRequestHeader('Cache-Control', 'no-cache')

      let lastIndex = 0
      let buffer = ''

      const parseStream = (fullText: string) => {
        // 仅处理新增片段
        const chunk = fullText.slice(lastIndex)
        lastIndex = fullText.length
        buffer += chunk
        // SSE 按双换行分隔事件
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''
        for (const ev of events) {
          const lines = ev.split('\n').filter((l) => l.startsWith('data: '))
          for (const line of lines) {
            const payload = line.slice(6)
            try {
              onChunk(JSON.parse(payload))
            } catch {
              // 忽略解析错误
            }
          }
        }
      }

      xhr.onprogress = () => {
        // 渐进式读取：xhr.responseText 包含目前接收到的全部响应体
        if (typeof xhr.responseText === 'string') {
          parseStream(xhr.responseText)
        }
      }

      xhr.onload = () => {
        // 确保最后一帧被解析
        if (typeof xhr.responseText === 'string') {
          parseStream(xhr.responseText)
        }
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve()
        } else {
          reject(new Error(xhr.responseText || `请求失败：${xhr.status}`))
        }
      }

      xhr.onerror = () => {
        reject(new Error('网络错误：无法连接到服务器'))
      }

      xhr.onabort = () => {
        reject(new Error('请求被中止'))
      }

      xhr.send(JSON.stringify({ content, mode }))
    })
  },
}

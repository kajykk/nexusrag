import client from './client'

export interface Doc {
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

export const docApi = {
  async list(kbId: string): Promise<Doc[]> {
    const { data } = await client.get(`/kb/${kbId}/documents`)
    return data.data
  },
  async upload(kbId: string, files: File[]): Promise<Doc[]> {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    const { data } = await client.post(`/kb/${kbId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data.data
  },
  async status(kbId: string, docId: string): Promise<Doc> {
    const { data } = await client.get(`/kb/${kbId}/documents/${docId}/status`)
    return data.data
  },
  async delete(kbId: string, docId: string): Promise<void> {
    await client.delete(`/kb/${kbId}/documents/${docId}`)
  },
}

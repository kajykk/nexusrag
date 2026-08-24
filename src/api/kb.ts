import client from './client'

export interface KnowledgeBase {
  id: string
  user_id: string
  name: string
  description: string
  document_count: number
  created_at: string
  vectorCount?: number
}

export const kbApi = {
  async list(): Promise<KnowledgeBase[]> {
    const { data } = await client.get('/kb')
    return data.data
  },
  async get(id: string): Promise<KnowledgeBase & { vectorCount: number }> {
    const { data } = await client.get(`/kb/${id}`)
    return data.data
  },
  async create(name: string, description = ''): Promise<KnowledgeBase> {
    const { data } = await client.post('/kb', { name, description })
    return data.data
  },
  async update(id: string, payload: { name?: string; description?: string }): Promise<KnowledgeBase> {
    const { data } = await client.patch(`/kb/${id}`, payload)
    return data.data
  },
  async delete(id: string): Promise<void> {
    await client.delete(`/kb/${id}`)
  },
}

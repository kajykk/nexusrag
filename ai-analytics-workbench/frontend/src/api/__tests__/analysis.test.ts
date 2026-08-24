import { afterEach, describe, expect, it, vi } from 'vitest'

import client from '../client'
import { analysisApi } from '../analysis'

vi.mock('../client', () => {
  const ax = {
    post: vi.fn(),
    get: vi.fn(),
    defaults: { baseURL: '/api/v1', timeout: 60000 },
    interceptors: { response: { handlers: [] } },
  }
  return { default: ax }
})

const mockClient = client as unknown as {
  post: ReturnType<typeof vi.fn>
  get: ReturnType<typeof vi.fn>
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('api/analysis', () => {
  it('create 调用 POST /analyses，发送 dataset_id 与 question', async () => {
    mockClient.post.mockResolvedValueOnce({ data: { analysis_id: 11 } })

    const res = await analysisApi.create(5, '求每个城市的总销量')

    expect(mockClient.post).toHaveBeenCalledWith('/analyses', {
      dataset_id: 5,
      question: '求每个城市的总销量',
    })
    expect(res).toEqual({ analysis_id: 11 })
  })

  it('list 无参数时调用 GET /analyses（空 params）', async () => {
    mockClient.get.mockResolvedValueOnce({ data: [] })

    await analysisApi.list()
    expect(mockClient.get).toHaveBeenCalledWith('/analyses', { params: {} })
  })

  it('list 带 datasetId 时透传到 query', async () => {
    mockClient.get.mockResolvedValueOnce({ data: [{ id: 1 }] })

    await analysisApi.list(42)
    expect(mockClient.get).toHaveBeenCalledWith('/analyses', { params: { dataset_id: 42 } })
  })

  it('detail 调用 GET /analyses/{id}', async () => {
    mockClient.get.mockResolvedValueOnce({ data: { id: 7 } })

    const res = await analysisApi.detail(7)
    expect(mockClient.get).toHaveBeenCalledWith('/analyses/7')
    expect(res).toEqual({ id: 7 })
  })
})

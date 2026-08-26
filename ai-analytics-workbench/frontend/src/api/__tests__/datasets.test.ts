import { afterEach, describe, expect, it, vi } from 'vitest'

import client from '../client'
import { datasetsApi } from '../datasets'

vi.mock('../client', () => {
  const ax = {
    post: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
    defaults: { baseURL: '/api/v1', timeout: 60000 },
    interceptors: { response: { handlers: [] } },
  }
  return { default: ax }
})

const mockClient = client as unknown as {
  post: ReturnType<typeof vi.fn>
  get: ReturnType<typeof vi.fn>
  delete: ReturnType<typeof vi.fn>
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('api/datasets', () => {
  it('upload 使用 multipart 上传 FormData 并解包 .data', async () => {
    const file = new File(['col1,col2\n1,2\n'], 'test.csv', { type: 'text/csv' })
    const created = { id: 7, name: '我的数据集' }
    mockClient.post.mockResolvedValueOnce({ data: created })

    const res = await datasetsApi.upload(file, '我的数据集', '描述')

    // 不手动指定 multipart 头（由浏览器生成带 boundary 的 Content-Type）
    expect(mockClient.post).toHaveBeenCalledWith('/datasets/upload', expect.any(FormData))
    // 与其它 API 方法契约一致：返回解包后的业务数据
    expect(res).toEqual(created)

    const sentForm = mockClient.post.mock.calls[0][1] as FormData
    expect(sentForm.get('file')).toBe(file)
    expect(sentForm.get('name')).toBe('我的数据集')
    expect(sentForm.get('description')).toBe('描述')
  })

  it('list 调用 GET /datasets 并返回 data', async () => {
    const list = [
      { id: 1, name: 'a' },
      { id: 2, name: 'b' },
    ]
    mockClient.get.mockResolvedValueOnce({ data: list })

    const res = await datasetsApi.list()
    expect(mockClient.get).toHaveBeenCalledWith('/datasets')
    expect(res).toEqual(list)
  })

  it('detail 调用 GET /datasets/{id}', async () => {
    mockClient.get.mockResolvedValueOnce({ data: { id: 9 } })

    const res = await datasetsApi.detail(9)
    expect(mockClient.get).toHaveBeenCalledWith('/datasets/9')
    expect(res).toEqual({ id: 9 })
  })

  it('remove 调用 DELETE /datasets/{id}', async () => {
    mockClient.delete.mockResolvedValueOnce({ data: { ok: true } })

    const res = await datasetsApi.remove(3)
    expect(mockClient.delete).toHaveBeenCalledWith('/datasets/3')
    expect(res).toEqual({ ok: true })
  })
})

import { afterEach, describe, expect, it, vi } from 'vitest'

import client from '../client'
import { reportsApi } from '../reports'

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

describe('api/reports', () => {
  it('create 调用 POST /reports，默认 title=数据分析报告', async () => {
    mockClient.post.mockResolvedValueOnce({ data: { id: 1 } })

    const res = await reportsApi.create(99)
    expect(mockClient.post).toHaveBeenCalledWith('/reports', {
      analysis_id: 99,
      title: '数据分析报告',
    })
    expect(res).toEqual({ id: 1 })
  })

  it('create 允许自定义 title', async () => {
    mockClient.post.mockResolvedValueOnce({ data: { id: 2 } })

    await reportsApi.create(1, '自定义报告')
    expect(mockClient.post).toHaveBeenCalledWith('/reports', {
      analysis_id: 1,
      title: '自定义报告',
    })
  })

  it('detail 调用 GET /reports/{id}', async () => {
    mockClient.get.mockResolvedValueOnce({ data: { id: 5 } })

    const res = await reportsApi.detail(5)
    expect(mockClient.get).toHaveBeenCalledWith('/reports/5')
    expect(res).toEqual({ id: 5 })
  })

  it('exportPdf 调用 POST /reports/{id}/export-pdf', async () => {
    mockClient.post.mockResolvedValueOnce({ data: { pdf_path: 'reports/report_1.pdf' } })

    const res = await reportsApi.exportPdf(5)
    expect(mockClient.post).toHaveBeenCalledWith('/reports/5/export-pdf')
    expect(res).toEqual({ pdf_path: 'reports/report_1.pdf' })
  })

  describe('downloadUrl', () => {
    const orig = import.meta.env.VITE_API_BASE_URL

    it('VITE_API_BASE_URL 未设置时使用相对前缀 /api/v1', () => {
      // 注意：直接赋值 undefined 会被 Vite define 替换为字符串 "undefined"
      // 通过 delete 移除键来模拟未设置
      delete (import.meta.env as unknown as Record<string, unknown>).VITE_API_BASE_URL
      expect(reportsApi.downloadUrl(7)).toBe('/api/v1/reports/7/download')
    })

    it('VITE_API_BASE_URL 设置时拼接绝对 URL', () => {
      ;(import.meta.env as unknown as Record<string, unknown>).VITE_API_BASE_URL =
        'https://api.example.com'
      expect(reportsApi.downloadUrl(7)).toBe('https://api.example.com/api/v1/reports/7/download')
    })

    it('恢复环境变量后回归默认行为', () => {
      if (orig !== undefined) {
        ;(import.meta.env as unknown as Record<string, unknown>).VITE_API_BASE_URL = orig
      } else {
        delete (import.meta.env as unknown as Record<string, unknown>).VITE_API_BASE_URL
      }
      expect(reportsApi.downloadUrl(1)).toMatch(/\/api\/v1\/reports\/1\/download$/)
    })
  })
})

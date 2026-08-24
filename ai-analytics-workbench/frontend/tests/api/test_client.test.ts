import { describe, expect, it } from 'vitest'
import client from '@/api/client'

type RejectedHandler = (err: unknown) => Promise<never>

function getRejectedHandler(): RejectedHandler | undefined {
  const interceptors = client.interceptors.response as unknown as {
    handlers: Array<{ rejected?: RejectedHandler } | null>
  }
  return interceptors.handlers[0]?.rejected ?? undefined
}

describe('api/client - axios 实例与拦截器', () => {
  it('baseURL is set correctly：默认走代理时为 /api/v1', () => {
    expect(client.defaults.baseURL).toBe('/api/v1')
  })

  it('response interceptor rejects with message：从 response.data.detail 提取错误信息', async () => {
    const rejected = getRejectedHandler()
    expect(typeof rejected).toBe('function')

    const err = {
      response: { data: { detail: '数据集不存在' } },
      message: 'Network Error',
    }
    await expect(rejected?.(err)).rejects.toThrow('数据集不存在')
  })

  it('response interceptor：detail 缺失时回退到 error.message', async () => {
    const rejected = getRejectedHandler()

    const err = { message: 'Network Error' }
    await expect(rejected?.(err)).rejects.toThrow('Network Error')
  })

  it('response interceptor：detail 与 message 都缺失时使用默认文案', async () => {
    const rejected = getRejectedHandler()

    const err = {}
    await expect(rejected?.(err)).rejects.toThrow('请求失败')
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import client from '../client'

type FulfilledHandler = (resp: unknown) => unknown
type RejectedHandler = (err: unknown) => Promise<never>

function getHandlers(): Array<{
  fulfilled?: FulfilledHandler
  rejected?: RejectedHandler
} | null> {
  const interceptors = client.interceptors.response as unknown as {
    handlers: Array<{ fulfilled?: FulfilledHandler; rejected?: RejectedHandler } | null>
  }
  return interceptors.handlers
}

function getRejected(): RejectedHandler | undefined {
  return getHandlers()[0]?.rejected ?? undefined
}

function getFulfilled(): FulfilledHandler | undefined {
  return getHandlers()[0]?.fulfilled ?? undefined
}

describe('api/client - axios 实例与拦截器', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('baseURL 应当包含 /api/v1 前缀（默认走代理）', async () => {
    const mod = await import('../client')
    expect(mod.default.defaults.baseURL).toMatch(/\/api\/v1\/?$/)
  })

  it('请求超时配置为 60000ms', async () => {
    const mod = await import('../client')
    expect(mod.default.defaults.timeout).toBe(60000)
  })

  it('响应拦截器：成功请求透传 resp', async () => {
    const okResponse = { status: 200, data: { ok: 1 }, statusText: 'OK', headers: {}, config: {} }
    const fulfilled = getFulfilled()
    expect(typeof fulfilled).toBe('function')
    expect(fulfilled?.(okResponse)).toEqual(okResponse)
  })

  it('响应拦截器：优先使用 response.data.detail', async () => {
    const rejected = getRejected()
    expect(typeof rejected).toBe('function')
    const err = { response: { data: { detail: '邮箱或密码错误' } }, message: 'Network Error' }
    await expect(rejected?.(err)).rejects.toThrow('邮箱或密码错误')
  })

  it('响应拦截器：回退到 error.message', async () => {
    const rejected = getRejected()
    const err = { message: 'Network Error' }
    await expect(rejected?.(err)).rejects.toThrow('Network Error')
  })

  it('响应拦截器：detail 与 message 都缺失时使用默认文案', async () => {
    const rejected = getRejected()
    const err = {}
    await expect(rejected?.(err)).rejects.toThrow('请求失败')
  })

  it('响应拦截器：rejected 必须返回 Promise（reject 形式）', async () => {
    const rejected = getRejected()
    const result = rejected?.({ response: { data: { detail: 'x' } } })
    expect(result).toBeInstanceOf(Promise)
    await expect(result).rejects.toBeInstanceOf(Error)
  })
})

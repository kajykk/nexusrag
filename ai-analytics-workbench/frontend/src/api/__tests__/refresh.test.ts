import { afterEach, describe, expect, it } from 'vitest'

import {
  clearTokens,
  getAccessToken,
  refreshAccessToken,
  saveTokens,
} from '../client'

afterEach(() => clearTokens())

describe('refreshAccessToken', () => {
  it('成功时返回新 access token 并持久化双 token', async () => {
    saveTokens('stale-access', 'valid-refresh')
    const post = async () => ({
      data: { access_token: 'new-access', refresh_token: 'new-refresh' },
    })

    const token = await refreshAccessToken(post)

    expect(token).toBe('new-access')
    expect(getAccessToken()).toBe('new-access')
    expect(localStorage.getItem('refresh_token')).toBe('new-refresh')
  })

  it('无 refresh 凭据时直接返回 null（不发起请求）', async () => {
    clearTokens()
    let called = 0
    const post = async () => {
      called += 1
      return { data: {} }
    }

    const token = await refreshAccessToken(post)

    expect(token).toBeNull()
    expect(called).toBe(0)
  })

  it('刷新失败时返回 null 并清空本地凭据', async () => {
    saveTokens('a', 'expired-refresh')
    const post = async () => {
      throw new Error('401')
    }

    const token = await refreshAccessToken(post)

    expect(token).toBeNull()
    expect(getAccessToken()).toBeNull()
    expect(localStorage.getItem('refresh_token')).toBeNull()
  })
})

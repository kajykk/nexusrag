import axios from 'axios'

/** 统一 API 前缀：其它模块（静态资源、下载链接）应从 getApiBase() 派生 */
export function getApiBase(): string {
  return import.meta.env.VITE_API_BASE_URL
    ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
    : '/api/v1'
}

/** 模块加载时的快照（仅供常量场景使用；运行时请用 getApiBase()） */
export const API_BASE = getApiBase()

const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY)
}

/** 登录/刷新成功后保存双 token */
export function saveTokens(access: string, refresh?: string): void {
  localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

/** 携带 HTTP 状态码与原始响应体的错误类型，调用方可据此区分 401/403/404 等 */
export class ApiError extends Error {
  readonly status?: number
  readonly data?: unknown

  constructor(message: string, status?: number, data?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

function formatDetail(detail: unknown): string | undefined {
  if (typeof detail === 'string') return detail
  // FastAPI 422 校验错误：detail 为 [{ loc, msg, type }, ...]
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string } | undefined
    return first?.msg ?? '请求参数校验失败'
  }
  if (detail && typeof detail === 'object' && 'msg' in (detail as Record<string, unknown>)) {
    return String((detail as Record<string, unknown>).msg)
  }
  return undefined
}

type PostLike = (url: string, body?: unknown) => Promise<{ data: unknown }>

/**
 * 用 refresh token 换取新 token 对；失败返回 null 并清理本地凭据。
 * postImpl 供测试注入；生产使用独立 axios 实例（不走业务拦截器，避免递归刷新）。
 */
export async function refreshAccessToken(postImpl: PostLike = axios.post): Promise<string | null> {
  const refreshToken = localStorage.getItem(REFRESH_KEY)
  if (!refreshToken) return null
  try {
    const resp = await postImpl(`${getApiBase()}/auth/refresh`, { refresh_token: refreshToken })
    const body = resp.data as { access_token?: string; refresh_token?: string }
    if (!body?.access_token) throw new Error('empty access_token')
    saveTokens(body.access_token, body.refresh_token)
    return body.access_token
  } catch {
    clearTokens()
    return null
  }
}

// 单飞：并发 401 共享同一次刷新请求
let refreshing: Promise<string | null> | null = null

function isRefreshUrl(url?: string): boolean {
  return typeof url === 'string' && url.includes('/auth/refresh')
}

const client = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
})

// 请求拦截：自动携带 JWT（登录后由认证模块写入 localStorage 的 access_token）
client.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一错误处理；401 时尝试单飞刷新并重放一次原请求
client.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const status = error.response?.status as number | undefined
    const data = error.response?.data
    const original = error.config as
      | (typeof error.config & { _retried?: boolean })
      | undefined

    const msg = formatDetail(data?.detail) || error.message || '请求失败'

    if (
      status === 401 &&
      original &&
      !original._retried &&
      !isRefreshUrl(original.url) &&
      localStorage.getItem(REFRESH_KEY)
    ) {
      original._retried = true
      refreshing = refreshing ?? refreshAccessToken().finally(() => (refreshing = null))
      const newToken = await refreshing
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return client(original)
      }
    }

    if (status === 401) {
      // 无 refresh 凭据或刷新失败：清空本地状态
      clearTokens()
    }
    return Promise.reject(new ApiError(msg, status, data))
  },
)

export default client

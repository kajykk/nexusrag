/**
 * Axios 实例 - 全局拦截器，自动注入 token
 *
 * 401 处理：单飞锁防并发跳转，自动清除登录态并携带 redirect 参数跳转登录页。
 */
import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('nexus_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 401 单飞锁：避免并发请求触发多次整页跳转
let redirectingToLogin = false

function redirectToLogin() {
  if (redirectingToLogin) return
  redirectingToLogin = true

  // 已在登录页则不跳转
  if (window.location.pathname.startsWith('/login')) {
    redirectingToLogin = false
    return
  }

  // 清除登录态
  localStorage.removeItem('nexus_token')
  localStorage.removeItem('nexus_user')

  // 保存当前路径作为 redirect 参数
  const current = window.location.pathname + window.location.search
  const loginUrl = `/login?redirect=${encodeURIComponent(current)}`
  window.location.assign(loginUrl)
}

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      redirectToLogin()
    }
    return Promise.reject(error)
  },
)

export default client
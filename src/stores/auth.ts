import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type User } from '@/api/auth'

const TOKEN_KEY = 'nexus_token'
const USER_KEY = 'nexus_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!token.value)

  function restore() {
    const t = localStorage.getItem(TOKEN_KEY)
    const u = localStorage.getItem(USER_KEY)
    if (t) token.value = t
    if (u) {
      try {
        user.value = JSON.parse(u)
      } catch {
        localStorage.removeItem(USER_KEY)
      }
    }
  }

  function persist(t: string, u: User) {
    token.value = t
    user.value = u
    localStorage.setItem(TOKEN_KEY, t)
    localStorage.setItem(USER_KEY, JSON.stringify(u))
  }

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const res = await authApi.login(email, password)
      persist(res.token, res.user)
    } finally {
      loading.value = false
    }
  }

  async function register(email: string, password: string, name: string) {
    loading.value = true
    try {
      const res = await authApi.register(email, password, name)
      persist(res.token, res.user)
    } finally {
      loading.value = false
    }
  }

  async function demoLogin() {
    loading.value = true
    try {
      const res = await authApi.demo()
      persist(res.token, res.user)
    } finally {
      loading.value = false
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, loading, isLoggedIn, restore, login, register, demoLogin, logout }
})

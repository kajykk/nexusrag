/**
 * 主题切换 composable
 *
 * 模块级单例，所有调用者共享同一个 theme ref。
 * 默认暗色，通过 localStorage 持久化，未保存时跟随系统偏好。
 * 需在 main.ts 或 App.vue 挂载时调用 initTheme() 初始化，
 * 同时 index.html 中有内联脚本防止 FOUC。
 */
import { ref, computed } from 'vue'

type Theme = 'light' | 'dark'

const STORAGE_KEY = 'theme'

const theme = ref<Theme>('dark')

function getSavedTheme(): Theme | null {
  const saved = localStorage.getItem(STORAGE_KEY)
  return saved === 'light' || saved === 'dark' ? saved : null
}

function resolveTheme(): Theme {
  const saved = getSavedTheme()
  if (saved) return saved
  if (typeof window !== 'undefined' && window.matchMedia) {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return 'dark'
}

function applyTheme(t: Theme) {
  document.documentElement.classList.toggle('light', t === 'light')
  document.documentElement.classList.toggle('dark', t === 'dark')
  localStorage.setItem(STORAGE_KEY, t)
}

/**
 * 初始化主题（在 app 挂载前调用）
 */
export function initTheme() {
  const t = resolveTheme()
  theme.value = t
  applyTheme(t)
}

/**
 * 主题切换 hook
 */
export function useTheme() {
  const toggleTheme = () => {
    const next = theme.value === 'light' ? 'dark' : 'light'
    theme.value = next
    applyTheme(next)
  }

  const setTheme = (t: Theme) => {
    theme.value = t
    applyTheme(t)
  }

  return {
    /** 当前主题 ref */
    theme,
    /** 是否为暗色 */
    isDark: computed(() => theme.value === 'dark'),
    /** 切换主题 */
    toggleTheme,
    /** 设置指定主题 */
    setTheme,
  }
}
/**
 * Toast 全局轻提示
 *
 * 模块级单例状态，任何组件内调用 useToast() 都能读写同一列表。
 * 替代 alert() 的错误提示体验。
 */
import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  type: ToastType
  message: string
}

const toasts = ref<ToastItem[]>([])
let seq = 0

function push(type: ToastType, message: string, duration = 3200): number {
  const id = ++seq
  toasts.value.push({ id, type, message })
  if (duration > 0) {
    setTimeout(() => remove(id), duration)
  }
  return id
}

function remove(id: number) {
  const idx = toasts.value.findIndex((t) => t.id === id)
  if (idx !== -1) toasts.value.splice(idx, 1)
}

export function useToast() {
  return {
    /** 全部 toast 列表（供 Toast.vue 渲染） */
    toasts,
    success: (message: string) => push('success', message),
    error: (message: string, duration = 5000) => push('error', message, duration),
    info: (message: string) => push('info', message),
    remove,
  }
}

export function errorMessage(e: unknown, fallback = '操作失败'): string {
  const err = e as { response?: { data?: { error?: string } }; message?: string } | null
  return err?.response?.data?.error || err?.message || fallback
}
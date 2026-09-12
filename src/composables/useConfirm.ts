/**
 * 确认对话框 composable
 *
 * 模块级单例，通过 promise 驱动：调用 confirm() 返回 Promise<boolean>，
 * 用户确认后 settle(true)，取消后 settle(false)。
 * 需配合 ConfirmDialog.vue 使用。
 */
import { ref, type Ref } from 'vue'

export interface ConfirmOptions {
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  /** 确认按钮显示为红色（危险操作） */
  danger?: boolean
}

export interface ConfirmState {
  open: boolean
  options: ConfirmOptions
}

const state: Ref<ConfirmState> = ref({ open: false, options: {} })
let resolver: ((v: boolean) => void) | null = null

export function useConfirm() {
  function confirm(options: ConfirmOptions = {}): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      resolver = resolve
      state.value = { open: true, options }
    })
  }

  function settle(result: boolean) {
    state.value = { open: false, options: {} }
    resolver?.(result)
    resolver = null
  }

  return { confirm, settle, state }
}
import type { WSProgressMessage } from './types'

/**
 * WebSocket 进度订阅工具。
 *
 * 自动根据环境变量决定连接地址，
 * 收到消息后调用 onMessage 回调。
 */
export function subscribeProgress(
  analysisId: number,
  onMessage: (msg: WSProgressMessage) => void,
  onClose?: () => void,
): WebSocket {
  const wsBase =
    import.meta.env.VITE_WS_BASE_URL ||
    `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`

  // 服务端要求 JWT：通过查询参数携带（浏览器 WS 无法自定义请求头）
  const token = localStorage.getItem('access_token') || ''
  const wsUrl = `${wsBase}/ws/analysis/${analysisId}?token=${encodeURIComponent(token)}`
  const ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as WSProgressMessage
      onMessage(data)
    } catch (e) {
      console.error('[ws] 解析消息失败', e)
    }
  }

  ws.onclose = () => {
    onClose?.()
  }

  ws.onerror = (e) => {
    console.error('[ws] 连接错误', e)
  }

  return ws
}

/**
 * 可重连的 WebSocket 订阅控制器。
 *
 * 设计：
 * - 自动重连：在意外关闭（close code != 1000）时按指数退避重连
 * - 手动关闭：调用 `close()` 不会触发重连
 * - 最大重试次数：默认 5 次，超过后停止
 * - 退避基数：默认 1000ms，每次翻倍，封顶 30000ms
 */
export interface ReconnectingWSController {
  /** 主动关闭，不触发重连。 */
  close: () => void
  /** 当前重连次数（手动 close 后归零）。 */
  retryCount: number
}

export interface ReconnectOptions {
  /** 最大重试次数，默认 5。 */
  maxRetries?: number
  /** 初始退避毫秒数，默认 1000。 */
  baseDelayMs?: number
  /** 退避上限毫秒数，默认 30000。 */
  maxDelayMs?: number
}

/**
 * 订阅分析进度，断线时自动重连。
 *
 * 用法：
 * ```ts
 * const ctrl = subscribeProgressWithReconnect(analysisId, onMessage)
 * // 用户切换页面时主动关闭
 * onUnmounted(() => ctrl.close())
 * ```
 */
export function subscribeProgressWithReconnect(
  analysisId: number,
  onMessage: (msg: WSProgressMessage) => void,
  options: ReconnectOptions = {},
): ReconnectingWSController {
  const { maxRetries = 5, baseDelayMs = 1000, maxDelayMs = 30000 } = options

  let ws: WebSocket | null = null
  let retryCount = 0
  let manualClose = false
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  const wsBase =
    import.meta.env.VITE_WS_BASE_URL ||
    `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`
  // 服务端要求 JWT：通过查询参数携带（浏览器 WS 无法自定义请求头）
  const token = localStorage.getItem('access_token') || ''
  const wsUrl = `${wsBase}/ws/analysis/${analysisId}?token=${encodeURIComponent(token)}`

  function clearReconnectTimer(): void {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function scheduleReconnect(): void {
    if (manualClose) return
    if (retryCount >= maxRetries) {
      console.warn(`[ws] 重连次数已达上限 ${maxRetries}，停止重连`)
      return
    }
    const delay = Math.min(baseDelayMs * 2 ** retryCount, maxDelayMs)
    retryCount += 1
    console.info(`[ws] ${delay}ms 后第 ${retryCount}/${maxRetries} 次重连`)
    clearReconnectTimer()
    reconnectTimer = setTimeout(() => {
      if (!manualClose) connect()
    }, delay)
  }

  function connect(): void {
    ws = new WebSocket(wsUrl)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSProgressMessage
        onMessage(data)
      } catch (e) {
        console.error('[ws] 解析消息失败', e)
      }
    }

    ws.onopen = () => {
      // 连接成功后重置重试计数，避免短暂抖动累积
      retryCount = 0
    }

    ws.onclose = (event) => {
      // 1000 = Normal Closure，仅在异常关闭时重连
      if (event.code !== 1000) {
        scheduleReconnect()
      }
    }

    ws.onerror = (e) => {
      console.error('[ws] 连接错误', e)
    }
  }

  connect()

  return {
    close() {
      manualClose = true
      clearReconnectTimer()
      // 手动关闭后重置计数，与接口注释语义一致（下次订阅从 0 开始）
      retryCount = 0
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close(1000, 'client close')
      } else if (ws) {
        ws.close()
      }
    },
    get retryCount() {
      return retryCount
    },
  }
}

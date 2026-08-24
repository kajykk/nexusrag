import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { subscribeProgress, subscribeProgressWithReconnect } from '@/api/ws'
import type { WSProgressMessage } from '@/api/types'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  url: string
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: ((event: { code: number; reason: string }) => void) | null = null
  onerror: ((event: unknown) => void) | null = null
  onopen: (() => void) | null = null
  readyState = 0
  closeCode: number | null = null
  closeReason: string | null = null

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }
  close(code = 1000, reason = '') {
    this.readyState = 3
    this.closeCode = code
    this.closeReason = reason
  }
}

describe('api/ws - subscribeProgress', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    ;(globalThis as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket
  })

  afterEach(() => {
    vi.restoreAllMocks()
    delete (globalThis as unknown as { WebSocket?: unknown }).WebSocket
  })

  it('subscribeProgress calls onMessage：正确解析消息并调用回调', () => {
    const onMessage = vi.fn()
    const ws = subscribeProgress(1, onMessage) as unknown as MockWebSocket

    const payload: WSProgressMessage = {
      analysis_id: 1,
      stage: 'running',
      progress: 50,
      message: '正在执行',
    }
    ws.onmessage!({ data: JSON.stringify(payload) })

    expect(onMessage).toHaveBeenCalledTimes(1)
    expect(onMessage).toHaveBeenCalledWith(payload)
  })

  it('subscribeProgress calls onClose：连接关闭时调用 onClose', () => {
    const onMessage = vi.fn()
    const onClose = vi.fn()
    const ws = subscribeProgress(1, onMessage, onClose) as unknown as MockWebSocket

    ws.onclose!({ code: 1000, reason: '' })

    expect(onClose).toHaveBeenCalledTimes(1)
    expect(onMessage).not.toHaveBeenCalled()
  })

  it('subscribeProgress 未传 onClose 时关闭不报错', () => {
    const onMessage = vi.fn()
    const ws = subscribeProgress(1, onMessage) as unknown as MockWebSocket

    expect(() => ws.onclose!({ code: 1000, reason: '' })).not.toThrow()
  })

  it('subscribeProgress 使用 analysisId 拼接 WebSocket URL', () => {
    subscribeProgress(42, vi.fn())
    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toContain('/ws/analysis/42')
  })
})

describe('api/ws - subscribeProgressWithReconnect', () => {
  beforeEach(() => {
    MockWebSocket.instances = []
    vi.useFakeTimers()
    ;(globalThis as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    delete (globalThis as unknown as { WebSocket?: unknown }).WebSocket
  })

  it('初次连接立即创建 WebSocket 实例', () => {
    subscribeProgressWithReconnect(1, vi.fn())
    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toContain('/ws/analysis/1')
  })

  it('异常关闭（code != 1000）后按指数退避重连', () => {
    subscribeProgressWithReconnect(2, vi.fn(), { baseDelayMs: 1000, maxRetries: 3 })

    // 初次连接
    expect(MockWebSocket.instances).toHaveLength(1)
    const firstWs = MockWebSocket.instances[0]

    // 模拟服务端异常关闭（code 1006 = abnormal closure）
    firstWs.onclose!({ code: 1006, reason: 'abnormal' })

    // 推进 500ms（< 1000ms），不应重连
    vi.advanceTimersByTime(500)
    expect(MockWebSocket.instances).toHaveLength(1)

    // 推进到 1000ms 后，应触发重连
    vi.advanceTimersByTime(600)
    expect(MockWebSocket.instances).toHaveLength(2)
  })

  it('正常关闭（code = 1000）不触发重连', () => {
    subscribeProgressWithReconnect(3, vi.fn(), { baseDelayMs: 1000 })

    const firstWs = MockWebSocket.instances[0]
    firstWs.onclose!({ code: 1000, reason: 'normal' })

    // 推进很久也不应重连
    vi.advanceTimersByTime(60000)
    expect(MockWebSocket.instances).toHaveLength(1)
  })

  it('主动 close 后不再触发重连', () => {
    const ctrl = subscribeProgressWithReconnect(4, vi.fn(), { baseDelayMs: 1000 })

    const firstWs = MockWebSocket.instances[0]
    firstWs.onclose!({ code: 1006, reason: 'abnormal' })

    // 主动关闭（在退避窗口内）
    ctrl.close()

    // 推进很久也不应重连
    vi.advanceTimersByTime(60000)
    expect(MockWebSocket.instances).toHaveLength(1)
  })

  it('重连成功后重置 retryCount', () => {
    subscribeProgressWithReconnect(5, vi.fn(), { baseDelayMs: 1000, maxRetries: 5 })

    // 第一次异常关闭 + 重连
    MockWebSocket.instances[0].onclose!({ code: 1006, reason: 'x' })
    vi.advanceTimersByTime(1000)
    expect(MockWebSocket.instances).toHaveLength(2)

    // 第二个连接 onopen 触发后 retryCount 应归零（隐式验证：再次异常关闭仍能继续重连）
    MockWebSocket.instances[1].onopen!()
    MockWebSocket.instances[1].onclose!({ code: 1006, reason: 'y' })

    // 退避从 1000ms 起算（不是 2000ms），说明 retryCount 已重置
    vi.advanceTimersByTime(1000)
    expect(MockWebSocket.instances).toHaveLength(3)
  })

  it('达到最大重试次数后停止重连', () => {
    subscribeProgressWithReconnect(6, vi.fn(), { baseDelayMs: 100, maxRetries: 2 })

    // 第 1 次重连
    MockWebSocket.instances[0].onclose!({ code: 1006, reason: '1' })
    vi.advanceTimersByTime(100)
    expect(MockWebSocket.instances).toHaveLength(2)

    // 第 2 次重连
    MockWebSocket.instances[1].onclose!({ code: 1006, reason: '2' })
    vi.advanceTimersByTime(200) // 第二次退避 100 * 2^1 = 200ms
    expect(MockWebSocket.instances).toHaveLength(3)

    // 第 3 次重连应被阻止（已达 maxRetries = 2）
    MockWebSocket.instances[2].onclose!({ code: 1006, reason: '3' })
    vi.advanceTimersByTime(10000)
    expect(MockWebSocket.instances).toHaveLength(3)
  })
})


import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { AnalysisItem } from '@/api/types'
import { analysisApi } from '@/api/analysis'
import { createPinia, setActivePinia } from 'pinia'

import { useAnalysisStore } from '../analysis'

vi.mock('@/api/analysis', () => ({
  analysisApi: {
    list: vi.fn(),
    detail: vi.fn(),
    create: vi.fn(),
  },
}))

const listMock = analysisApi.list as ReturnType<typeof vi.fn>
const detailMock = analysisApi.detail as ReturnType<typeof vi.fn>
const createMock = analysisApi.create as ReturnType<typeof vi.fn>

beforeEach(() => {
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.clearAllMocks()
})

const sampleList: AnalysisItem[] = [
  {
    id: 1,
    dataset_id: 5,
    question: '问题 A',
    status: 'succeeded',
    code_type: 'python',
    created_at: '2026-01-01',
    completed_at: '2026-01-01',
  },
  {
    id: 2,
    dataset_id: 5,
    question: '问题 B',
    status: 'failed',
    code_type: 'python',
    error_message: 'boom',
    created_at: '2026-01-02',
    completed_at: null,
  },
]

describe('stores/analysis', () => {
  it('初始状态：list 空，current null，progress 全 0', () => {
    const store = useAnalysisStore()
    expect(store.list).toEqual([])
    expect(store.current).toBeNull()
    expect(store.loading).toBe(false)
    expect(store.progress).toEqual({ stage: '', percent: 0, message: '' })
  })

  it('fetchList：成功填充 list 并复位 loading', async () => {
    listMock.mockResolvedValueOnce(sampleList)
    const store = useAnalysisStore()
    const promise = store.fetchList()
    expect(store.loading).toBe(true)
    await promise
    expect(store.list).toEqual(sampleList)
    expect(store.loading).toBe(false)
  })

  it('fetchList：透传 datasetId 给 api', async () => {
    listMock.mockResolvedValueOnce([])
    const store = useAnalysisStore()
    await store.fetchList(42)
    expect(listMock).toHaveBeenCalledWith(42)
  })

  it('fetchList：抛错时仍复位 loading', async () => {
    listMock.mockRejectedValueOnce(new Error('boom'))
    const store = useAnalysisStore()
    await expect(store.fetchList()).rejects.toThrow('boom')
    expect(store.loading).toBe(false)
  })

  it('fetchDetail：填充 current 并返回值', async () => {
    detailMock.mockResolvedValueOnce(sampleList[0])
    const store = useAnalysisStore()
    const res = await store.fetchDetail(1)
    expect(detailMock).toHaveBeenCalledWith(1)
    expect(store.current).toEqual(sampleList[0])
    expect(res).toEqual(sampleList[0])
  })

  it('create：返回新 analysis_id', async () => {
    createMock.mockResolvedValueOnce({ analysis_id: 17 })
    const store = useAnalysisStore()
    const id = await store.create(8, '统计每个城市的销量')
    expect(createMock).toHaveBeenCalledWith(8, '统计每个城市的销量')
    expect(id).toBe(17)
  })

  it('updateProgress：直接覆盖 progress 对象', () => {
    const store = useAnalysisStore()
    store.updateProgress('running', 42, '正在执行 Pandas 代码')
    expect(store.progress).toEqual({
      stage: 'running',
      percent: 42,
      message: '正在执行 Pandas 代码',
    })
  })

  it('updateProgress：再次调用应替换而非合并旧字段', () => {
    const store = useAnalysisStore()
    store.updateProgress('running', 50, 'message-1')
    store.updateProgress('succeeded', 100, 'message-2')
    expect(store.progress).toEqual({ stage: 'succeeded', percent: 100, message: 'message-2' })
  })
})

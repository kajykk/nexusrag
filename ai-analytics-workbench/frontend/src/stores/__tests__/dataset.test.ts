import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { DatasetDetail, DatasetListItem } from '@/api/types'
import { datasetsApi } from '@/api/datasets'
import { createPinia, setActivePinia } from 'pinia'

import { useDatasetStore } from '../dataset'

vi.mock('@/api/datasets', () => ({
  datasetsApi: {
    list: vi.fn(),
    detail: vi.fn(),
    upload: vi.fn(),
    remove: vi.fn(),
  },
}))

const listMock = datasetsApi.list as ReturnType<typeof vi.fn>
const detailMock = datasetsApi.detail as ReturnType<typeof vi.fn>
const uploadMock = datasetsApi.upload as ReturnType<typeof vi.fn>
const removeMock = datasetsApi.remove as ReturnType<typeof vi.fn>

beforeEach(() => {
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.clearAllMocks()
})

const sampleList: DatasetListItem[] = [
  {
    id: 1,
    name: 'DS1',
    original_filename: 'a.csv',
    file_type: 'csv',
    row_count: 10,
    column_count: 3,
    created_at: '2026-01-01',
  },
  {
    id: 2,
    name: 'DS2',
    original_filename: 'b.xlsx',
    file_type: 'xlsx',
    row_count: 5,
    column_count: 2,
    created_at: '2026-01-02',
  },
]

const sampleDetail: DatasetDetail = {
  ...sampleList[0],
  columns_schema: [],
  preview: [],
  description: 'desc',
}

describe('stores/dataset', () => {
  it('初始状态：空 list，null current，loading=false', () => {
    const store = useDatasetStore()
    expect(store.list).toEqual([])
    expect(store.current).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('fetchList：成功后填充 list，loading 复位', async () => {
    listMock.mockResolvedValueOnce(sampleList)
    const store = useDatasetStore()
    const promise = store.fetchList()
    // 异步进行中 loading 应为 true
    expect(store.loading).toBe(true)
    await promise
    expect(store.list).toEqual(sampleList)
    expect(store.loading).toBe(false)
    expect(listMock).toHaveBeenCalledTimes(1)
  })

  it('fetchList：抛错时 finally 仍复位 loading', async () => {
    listMock.mockRejectedValueOnce(new Error('boom'))
    const store = useDatasetStore()
    await expect(store.fetchList()).rejects.toThrow('boom')
    expect(store.loading).toBe(false)
    expect(store.list).toEqual([])
  })

  it('fetchDetail：填充 current 并返回值', async () => {
    detailMock.mockResolvedValueOnce(sampleDetail)
    const store = useDatasetStore()
    const res = await store.fetchDetail(1)
    expect(detailMock).toHaveBeenCalledWith(1)
    expect(store.current).toEqual(sampleDetail)
    expect(res).toEqual(sampleDetail)
  })

  it('upload：调用 api 并刷新 list', async () => {
    uploadMock.mockResolvedValueOnce({ id: 9 })
    listMock.mockResolvedValueOnce(sampleList)
    const store = useDatasetStore()

    const file = new File(['x'], 'c.csv')
    const res = await store.upload(file, '新数据集', '描述')

    expect(uploadMock).toHaveBeenCalledWith(file, '新数据集', '描述')
    expect(res).toEqual({ id: 9 })
    expect(listMock).toHaveBeenCalledTimes(1)
    expect(store.list).toEqual(sampleList)
  })

  it('remove：调用 api 后刷新 list', async () => {
    removeMock.mockResolvedValueOnce(undefined)
    listMock.mockResolvedValueOnce([])
    const store = useDatasetStore()

    await store.remove(7)

    expect(removeMock).toHaveBeenCalledWith(7)
    expect(listMock).toHaveBeenCalledTimes(1)
    expect(store.list).toEqual([])
  })
})

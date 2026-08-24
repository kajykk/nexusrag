import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { datasetsApi } from '@/api/datasets'
import { useDatasetStore } from '@/stores/dataset'
import type { DatasetListItem } from '@/api/types'

vi.mock('@/api/datasets', () => ({
  datasetsApi: {
    list: vi.fn(),
    detail: vi.fn(),
    upload: vi.fn(),
    remove: vi.fn(),
  },
}))

const listMock = datasetsApi.list as ReturnType<typeof vi.fn>
const uploadMock = datasetsApi.upload as ReturnType<typeof vi.fn>

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

describe('stores/dataset', () => {
  it('initial state：list 为空、current 为 null', () => {
    const store = useDatasetStore()
    expect(store.list).toEqual([])
    expect(store.current).toBeNull()
  })

  it('fetchList updates list：mock datasetsApi.list 后更新 list', async () => {
    listMock.mockResolvedValueOnce(sampleList)
    const store = useDatasetStore()

    await store.fetchList()

    expect(listMock).toHaveBeenCalledTimes(1)
    expect(store.list).toEqual(sampleList)
  })

  it('upload calls api and refreshes list：调用 upload 后刷新 list', async () => {
    uploadMock.mockResolvedValueOnce({ id: 9 })
    listMock.mockResolvedValueOnce(sampleList)
    const store = useDatasetStore()

    const file = new File(['x'], 'c.csv')
    const res = await store.upload(file, '新数据集', '描述')

    expect(uploadMock).toHaveBeenCalledWith(file, '新数据集', '描述')
    expect(listMock).toHaveBeenCalledTimes(1)
    expect(store.list).toEqual(sampleList)
    expect(res).toEqual({ id: 9 })
  })
})

import client from './client'
import type { DatasetDetail, DatasetListItem } from './types'

export const datasetsApi = {
  /** 上传数据集 */
  upload(file: File, name: string, description: string) {
    const form = new FormData()
    form.append('file', file)
    form.append('name', name)
    form.append('description', description)
    return client.post('/datasets/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  /** 数据集列表 */
  list(): Promise<DatasetListItem[]> {
    return client.get('/datasets').then((r) => r.data)
  },

  /** 数据集详情 */
  detail(id: number): Promise<DatasetDetail> {
    return client.get(`/datasets/${id}`).then((r) => r.data)
  },

  /** 删除数据集 */
  remove(id: number) {
    return client.delete(`/datasets/${id}`).then((r) => r.data)
  },
}

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { datasetsApi } from '@/api/datasets'
import type { DatasetDetail, DatasetListItem } from '@/api/types'

export const useDatasetStore = defineStore('dataset', () => {
  const list = ref<DatasetListItem[]>([])
  const current = ref<DatasetDetail | null>(null)
  const loading = ref(false)
  // 请求序号守卫：慢响应返回时丢弃，防止旧数据覆盖新数据
  let listSeq = 0
  let detailSeq = 0

  async function fetchList() {
    const seq = ++listSeq
    loading.value = true
    try {
      const items = await datasetsApi.list()
      if (seq === listSeq) list.value = items
    } finally {
      if (seq === listSeq) loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    const seq = ++detailSeq
    loading.value = true
    try {
      const item = await datasetsApi.detail(id)
      if (seq !== detailSeq) return current.value
      current.value = item
      return item
    } finally {
      if (seq === detailSeq) loading.value = false
    }
  }

  async function upload(file: File, name: string, description: string) {
    const res = await datasetsApi.upload(file, name, description)
    await fetchList()
    return res
  }

  async function remove(id: number) {
    await datasetsApi.remove(id)
    await fetchList()
  }

  return { list, current, loading, fetchList, fetchDetail, upload, remove }
})

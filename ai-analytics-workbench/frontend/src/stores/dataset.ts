import { defineStore } from 'pinia'
import { ref } from 'vue'
import { datasetsApi } from '@/api/datasets'
import type { DatasetDetail, DatasetListItem } from '@/api/types'

export const useDatasetStore = defineStore('dataset', () => {
  const list = ref<DatasetListItem[]>([])
  const current = ref<DatasetDetail | null>(null)
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      list.value = await datasetsApi.list()
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    loading.value = true
    try {
      current.value = await datasetsApi.detail(id)
      return current.value
    } finally {
      loading.value = false
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

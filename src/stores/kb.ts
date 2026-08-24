import { defineStore } from 'pinia'
import { ref } from 'vue'
import { kbApi, type KnowledgeBase } from '@/api/kb'

export const useKbStore = defineStore('kb', () => {
  const list = ref<KnowledgeBase[]>([])
  const current = ref<KnowledgeBase | null>(null)
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      list.value = await kbApi.list()
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id: string) {
    loading.value = true
    try {
      current.value = await kbApi.get(id)
      return current.value
    } finally {
      loading.value = false
    }
  }

  async function create(name: string, description = '') {
    const kb = await kbApi.create(name, description)
    list.value.unshift(kb)
    return kb
  }

  async function remove(id: string) {
    await kbApi.delete(id)
    list.value = list.value.filter((k) => k.id !== id)
  }

  return { list, current, loading, fetchList, fetchOne, create, remove }
})

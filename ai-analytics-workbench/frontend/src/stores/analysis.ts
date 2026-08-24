import { defineStore } from 'pinia'
import { ref } from 'vue'
import { analysisApi } from '@/api/analysis'
import type { AnalysisItem } from '@/api/types'

export const useAnalysisStore = defineStore('analysis', () => {
  const list = ref<AnalysisItem[]>([])
  const current = ref<AnalysisItem | null>(null)
  const loading = ref(false)
  /** 当前进行中的任务进度 */
  const progress = ref<{ stage: string; percent: number; message: string }>({
    stage: '',
    percent: 0,
    message: '',
  })

  async function fetchList(datasetId?: number) {
    loading.value = true
    try {
      list.value = await analysisApi.list(datasetId)
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    const item = await analysisApi.detail(id)
    current.value = item
    return item
  }

  async function create(datasetId: number, question: string) {
    const res = await analysisApi.create(datasetId, question)
    return res.analysis_id as number
  }

  function updateProgress(stage: string, percent: number, message: string) {
    progress.value = { stage, percent, message }
  }

  return { list, current, loading, progress, fetchList, fetchDetail, create, updateProgress }
})

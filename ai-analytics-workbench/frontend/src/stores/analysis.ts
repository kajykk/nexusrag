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
  // 请求序号守卫：快速连续触发时丢弃过期响应，防止旧数据覆盖新数据
  let listSeq = 0
  let detailSeq = 0

  async function fetchList(datasetId?: number) {
    const seq = ++listSeq
    loading.value = true
    try {
      const items = await analysisApi.list(datasetId)
      if (seq === listSeq) list.value = items
    } finally {
      if (seq === listSeq) loading.value = false
    }
  }

  async function fetchDetail(id: number) {
    const seq = ++detailSeq
    const item = await analysisApi.detail(id)
    if (seq !== detailSeq) return current.value
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

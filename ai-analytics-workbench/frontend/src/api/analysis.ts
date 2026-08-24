import client from './client'
import type { AnalysisItem } from './types'

export const analysisApi = {
  /** 创建分析任务 */
  create(datasetId: number, question: string) {
    return client.post('/analyses', { dataset_id: datasetId, question }).then((r) => r.data)
  },

  /** 分析任务列表 */
  list(datasetId?: number): Promise<AnalysisItem[]> {
    const params = datasetId ? { dataset_id: datasetId } : {}
    return client.get('/analyses', { params }).then((r) => r.data)
  },

  /** 分析任务详情 */
  detail(id: number): Promise<AnalysisItem> {
    return client.get(`/analyses/${id}`).then((r) => r.data)
  },
}

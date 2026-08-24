import client from './client'
import type { ReportItem } from './types'

export const reportsApi = {
  /** 生成报告 */
  create(analysisId: number, title = '数据分析报告') {
    return client.post('/reports', { analysis_id: analysisId, title }).then((r) => r.data)
  },

  /** 报告详情 */
  detail(id: number): Promise<ReportItem> {
    return client.get(`/reports/${id}`).then((r) => r.data)
  },

  /** 导出 PDF */
  exportPdf(id: number) {
    return client.post(`/reports/${id}/export-pdf`).then((r) => r.data)
  },

  /** PDF 下载链接 */
  downloadUrl(id: number): string {
    const base = import.meta.env.VITE_API_BASE_URL
      ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
      : '/api/v1'
    return `${base}/reports/${id}/download`
  },
}

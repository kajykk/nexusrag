/** 共享类型定义。 */

export interface ColumnInfo {
  name: string
  dtype: string
  sample: unknown[]
  null_count: number
  unique_count: number
}

export interface DatasetListItem {
  id: number
  name: string
  original_filename: string
  file_type: string
  row_count: number
  column_count: number
  created_at: string | null
}

export interface DatasetDetail extends DatasetListItem {
  columns_schema: ColumnInfo[]
  preview: Record<string, unknown>[]
  description: string
}

export interface AnalysisItem {
  id: number
  dataset_id: number
  question: string
  status: 'pending' | 'running' | 'succeeded' | 'failed'
  code_type: string
  generated_code?: string
  result_data?: { result?: unknown; summary?: string }
  chart_config?: Record<string, unknown>
  chart_image?: string
  error_message?: string
  created_at: string | null
  completed_at: string | null
}

export interface ReportItem {
  id: number
  analysis_id: number
  title: string
  content_md?: string
  pdf_path?: string
  created_at: string | null
}

/** WebSocket 进度消息。 */
export interface WSProgressMessage {
  analysis_id: number
  stage: 'connected' | 'queued' | 'running' | 'succeeded' | 'failed'
  progress: number
  message: string
  data?: {
    result_data?: unknown
    chart_config?: Record<string, unknown>
    chart_image?: string
    generated_code?: string
    error?: string
  }
}

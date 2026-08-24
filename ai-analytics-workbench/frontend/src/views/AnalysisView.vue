<script setup lang="ts">
import { onMounted, ref, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useDatasetStore } from '@/stores/dataset'
import { useAnalysisStore } from '@/stores/analysis'
import { analysisApi } from '@/api/analysis'
import { subscribeProgress } from '@/api/ws'
import { reportsApi } from '@/api/reports'
import type { AnalysisItem, WSProgressMessage } from '@/api/types'

const datasetStore = useDatasetStore()
const analysisStore = useAnalysisStore()

const selectedDatasetId = ref<number | null>(null)
const question = ref('')
const submitting = ref(false)
const result = ref<AnalysisItem | null>(null)
const chartContainer = ref<HTMLDivElement | null>(null)
const chartImageBase = import.meta.env.VITE_API_BASE_URL || ''
let chartInstance: echarts.ECharts | null = null
let ws: WebSocket | null = null
const reportId = ref<number | null>(null)
const reportMsg = ref('')

onMounted(() => datasetStore.fetchList())

watch(
  () => analysisStore.progress.percent,
  () => {
    if (analysisStore.progress.stage === 'succeeded' && analysisStore.current) {
      result.value = analysisStore.current
      nextTick(() => renderChart())
    }
  },
)

function renderChart() {
  if (!chartContainer.value || !result.value?.chart_config) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartContainer.value)
  }
  chartInstance.setOption(result.value.chart_config, true)
}

async function submit() {
  if (!selectedDatasetId.value || !question.value.trim()) return
  submitting.value = true
  result.value = null
  reportId.value = null
  reportMsg.value = ''
  analysisStore.updateProgress('', 0, '')

  try {
    // 1. 创建分析任务
    const analysisId = await analysisStore.create(selectedDatasetId.value, question.value)

    // 2. 订阅 WebSocket 进度
    ws?.close()
    ws = subscribeProgress(analysisId, (msg: WSProgressMessage) => {
      analysisStore.updateProgress(msg.stage, msg.progress, msg.message)

      if (msg.stage === 'succeeded') {
        submitting.value = false
        analysisStore.fetchDetail(analysisId).then((item) => {
          result.value = item
          nextTick(() => renderChart())
        })
      } else if (msg.stage === 'failed') {
        submitting.value = false
      }
    })

    // 3. 兜底：若 WS 未及时推送，轮询查询
    setTimeout(async () => {
      if (submitting.value) {
        const item = await analysisApi.detail(analysisId)
        if (item.status === 'succeeded' || item.status === 'failed') {
          submitting.value = false
          result.value = item
          analysisStore.updateProgress(
            item.status === 'succeeded' ? 'succeeded' : 'failed',
            100,
            '',
          )
          if (item.status === 'succeeded') nextTick(() => renderChart())
        }
      }
    }, 30000)
  } catch (e) {
    submitting.value = false
    analysisStore.updateProgress('failed', 100, e instanceof Error ? e.message : String(e))
  }
}

const quickQuestions = [
  '数据集有哪些列？各列的类型是什么？',
  '统计数值列的描述性统计（均值、中位数、标准差）',
  '找出缺失值最多的列',
  '对分类列做分组汇总统计',
]

function useQuick(q: string) {
  question.value = q
}

async function generateReport() {
  if (!result.value?.id) return
  reportMsg.value = '生成中...'
  try {
    const res = await reportsApi.create(result.value.id)
    reportId.value = res.id
    reportMsg.value = '报告已生成'
  } catch (e) {
    reportMsg.value = `生成失败：${e instanceof Error ? e.message : String(e)}`
  }
}

async function exportPdf() {
  if (!reportId.value) return
  reportMsg.value = '导出 PDF 中...'
  try {
    await reportsApi.exportPdf(reportId.value)
    reportMsg.value = 'PDF 已就绪'
  } catch (e) {
    reportMsg.value = `导出失败：${e instanceof Error ? e.message : String(e)}`
  }
}

function resultRows(): Record<string, unknown>[] {
  const r = result.value?.result_data?.result as
    Record<string, unknown> | Record<string, unknown>[] | undefined
  if (Array.isArray(r) && r.length && typeof r[0] === 'object' && r[0] !== null) {
    return r as Record<string, unknown>[]
  }
  if (r && typeof r === 'object' && !Array.isArray(r)) {
    // {列: [值]} 形式
    const obj = r as Record<string, unknown[]>
    const keys = Object.keys(obj)
    if (keys.length && Array.isArray(obj[keys[0]])) {
      const len = obj[keys[0]].length
      return Array.from({ length: len }, (_, i) =>
        Object.fromEntries(keys.map((k) => [k, obj[k][i]])),
      )
    }
    return [r as Record<string, unknown>]
  }
  return []
}
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h2>数据分析</h2>
        <p class="subtitle">
          用自然语言提问，AI 自动生成代码并执行分析
        </p>
      </div>
    </header>

    <!-- 提问区 -->
    <div class="ask-panel">
      <div class="form-row">
        <label>选择数据集</label>
        <select v-model.number="selectedDatasetId">
          <option
            :value="null"
            disabled
          >
            请选择...
          </option>
          <option
            v-for="d in datasetStore.list"
            :key="d.id"
            :value="d.id"
          >
            {{ d.name }}（{{ d.row_count }} 行）
          </option>
        </select>
      </div>
      <div class="form-row">
        <label>分析需求</label>
        <textarea
          v-model="question"
          placeholder="例如：统计各地区的销售额总和并按降序排列"
          rows="3"
        />
      </div>
      <div class="quick-tags">
        <span class="tag-label">快捷提问：</span>
        <button
          v-for="q in quickQuestions"
          :key="q"
          class="tag"
          @click="useQuick(q)"
        >
          {{ q }}
        </button>
      </div>
      <div class="ask-actions">
        <button
          class="btn-primary"
          :disabled="submitting || !selectedDatasetId || !question.trim()"
          @click="submit"
        >
          {{ submitting ? '分析中...' : '开始分析' }}
        </button>
      </div>
    </div>

    <!-- 进度区 -->
    <div
      v-if="analysisStore.progress.stage"
      class="progress-panel"
    >
      <div class="progress-bar">
        <div
          class="progress-fill"
          :style="{ width: analysisStore.progress.percent + '%' }"
        />
      </div>
      <p class="progress-text">
        <span
          class="stage-badge"
          :class="analysisStore.progress.stage"
        >
          {{ analysisStore.progress.stage }}
        </span>
        {{ analysisStore.progress.message }}（{{ analysisStore.progress.percent }}%）
      </p>
    </div>

    <!-- 结果区 -->
    <div
      v-if="result"
      class="result-panel"
    >
      <div
        v-if="result.status === 'failed'"
        class="error-box"
      >
        <h4>❌ 分析失败</h4>
        <pre>{{ result.error_message }}</pre>
      </div>

      <template v-else>
        <!-- 结论摘要 -->
        <div
          v-if="result.result_data?.summary"
          class="summary-box"
        >
          <h4>💡 分析结论</h4>
          <p>{{ result.result_data.summary }}</p>
        </div>

        <!-- 图表区 -->
        <div class="chart-section">
          <h4>📈 可视化图表</h4>
          <div class="chart-tabs">
            <div
              ref="chartContainer"
              class="echarts-box"
              style="width: 100%; height: 400px"
            />
          </div>
          <div
            v-if="result.chart_image"
            class="server-chart"
          >
            <p class="chart-label">
              服务端渲染（Matplotlib）：
            </p>
            <img
              :src="chartImageBase + '/' + result.chart_image"
              alt="服务端图表"
            >
          </div>
        </div>

        <!-- 数据表格 -->
        <div
          v-if="resultRows().length"
          class="data-section"
        >
          <h4>📋 数据结果</h4>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th
                    v-for="key in Object.keys(resultRows()[0])"
                    :key="key"
                  >
                    {{ key }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(row, i) in resultRows().slice(0, 100)"
                  :key="i"
                >
                  <td
                    v-for="key in Object.keys(resultRows()[0])"
                    :key="key"
                  >
                    {{ row[key] }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p
            v-if="resultRows().length > 100"
            class="table-foot"
          >
            仅显示前 100 行，共 {{ resultRows().length }} 行
          </p>
        </div>

        <!-- 代码 -->
        <div class="code-section">
          <h4>🔧 生成的代码</h4>
          <pre><code>{{ result.generated_code }}</code></pre>
        </div>

        <!-- 报告操作 -->
        <div class="report-actions">
          <button
            class="btn-outline"
            @click="generateReport"
          >
            {{ reportId ? '重新生成报告' : '生成分析报告' }}
          </button>
          <button
            v-if="reportId"
            class="btn-outline"
            @click="exportPdf"
          >
            导出 PDF
          </button>
          <a
            v-if="reportId"
            :href="reportsApi.downloadUrl(reportId)"
            target="_blank"
            class="btn-outline"
          >
            下载 PDF
          </a>
          <span
            v-if="reportMsg"
            class="report-msg"
          >{{ reportMsg }}</span>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  margin-bottom: 24px;
}
.page-header h2 {
  margin: 0 0 4px;
  font-size: 24px;
}
.subtitle {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}
.ask-panel {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #e2e8f0;
  margin-bottom: 20px;
}
.form-row {
  margin-bottom: 16px;
}
.form-row label {
  display: block;
  font-size: 13px;
  color: #64748b;
  margin-bottom: 6px;
  font-weight: 500;
}
.form-row select,
.form-row textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
}
.quick-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.tag-label {
  font-size: 13px;
  color: #94a3b8;
}
.tag {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 4px 12px;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
}
.tag:hover {
  background: #e0e7ff;
  border-color: var(--primary);
  color: var(--primary);
}
.ask-actions {
  text-align: right;
}
.btn-primary {
  background: var(--primary);
  color: #fff;
  border: none;
  padding: 10px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-outline {
  display: inline-block;
  background: #fff;
  color: var(--primary);
  border: 1px solid var(--primary);
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  text-decoration: none;
  margin-right: 8px;
}
.progress-panel {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e2e8f0;
  margin-bottom: 20px;
}
.progress-bar {
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 12px;
}
.progress-fill {
  height: 100%;
  background: var(--primary);
  transition: width 0.4s ease;
}
.progress-text {
  font-size: 13px;
  color: #64748b;
  margin: 0;
}
.stage-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  margin-right: 8px;
  background: #e0e7ff;
  color: #4f46e5;
}
.stage-badge.succeeded {
  background: #dcfce7;
  color: #16a34a;
}
.stage-badge.failed {
  background: #fee2e2;
  color: #dc2626;
}
.result-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.error-box {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 12px;
  padding: 20px;
}
.error-box pre {
  background: #fff;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  color: #dc2626;
}
.summary-box {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 20px;
}
.summary-box h4 {
  margin: 0 0 8px;
}
.summary-box p {
  margin: 0;
  line-height: 1.6;
}
.chart-section,
.data-section,
.code-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e2e8f0;
}
.chart-section h4,
.data-section h4,
.code-section h4 {
  margin: 0 0 16px;
  font-size: 15px;
}
.echarts-box {
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  padding: 8px;
}
.server-chart {
  margin-top: 16px;
  border-top: 1px dashed #e2e8f0;
  padding-top: 16px;
}
.chart-label {
  font-size: 13px;
  color: #64748b;
  margin: 0 0 8px;
}
.server-chart img {
  max-width: 100%;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th {
  background: #f8fafc;
  padding: 10px;
  text-align: left;
  border-bottom: 2px solid #e2e8f0;
  white-space: nowrap;
}
td {
  padding: 10px;
  border-bottom: 1px solid #f1f5f9;
}
.table-foot {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 8px;
}
.code-section pre {
  background: #1e293b;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
  margin: 0;
}
.report-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.report-msg {
  font-size: 13px;
  color: #64748b;
}
</style>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import { reportsApi } from '@/api/reports'
import type { ReportItem } from '@/api/types'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const reports = ref<ReportItem[]>([])
const loading = ref(false)
const selected = ref<ReportItem | null>(null)
const renderedHtml = ref('')
let viewSeq = 0

async function fetchReports() {
  loading.value = true
  try {
    reports.value = await reportsApi.list()
  } finally {
    loading.value = false
  }
}

onMounted(fetchReports)

async function viewReport(id: number) {
  const seq = ++viewSeq
  renderedHtml.value = ''
  try {
    const item = await reportsApi.detail(id)
    // 丢弃过期响应：快速连续点击时防止旧报告覆盖新选择
    if (seq !== viewSeq) return
    selected.value = item
    renderedHtml.value = md.render(item.content_md || '')
  } catch (e) {
    if (seq === viewSeq) {
      console.error('[reports] 详情加载失败', e)
    }
  }
}

async function exportPdf(id: number) {
  try {
    await reportsApi.exportPdf(id)
    await fetchReports()
    if (selected.value?.id === id) await viewReport(id)
  } catch (e) {
    alert(`导出失败：${e instanceof Error ? e.message : String(e)}`)
  }
}
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h2>分析报告</h2>
        <p class="subtitle">
          查看 AI 生成的数据分析报告并导出 PDF
        </p>
      </div>
    </header>

    <div class="report-layout">
      <!-- 报告列表 -->
      <div class="report-list">
        <div
          v-if="loading"
          class="loading"
        >
          加载中...
        </div>
        <div
          v-else-if="reports.length === 0"
          class="empty"
        >
          暂无报告，请先在「数据分析」页生成报告
        </div>
        <div
          v-for="r in reports"
          :key="r.id"
          class="report-item"
          :class="{ active: selected?.id === r.id }"
          @click="viewReport(r.id)"
        >
          <h4>{{ r.title }}</h4>
          <p class="meta">
            报告 #{{ r.id }} · 分析 #{{ r.analysis_id }}
          </p>
          <p class="time">
            {{ r.created_at?.slice(0, 19).replace('T', ' ') }}
          </p>
          <div class="badges">
            <span
              v-if="r.pdf_path"
              class="badge pdf"
            >PDF</span>
          </div>
        </div>
      </div>

      <!-- 报告内容 -->
      <div class="report-content">
        <div
          v-if="!selected"
          class="empty-content"
        >
          <p>👈 从左侧选择一份报告查看</p>
        </div>
        <template v-else>
          <div class="content-toolbar">
            <h3>{{ selected.title }}</h3>
            <div>
              <button
                class="btn-outline"
                @click="exportPdf(selected.id)"
              >
                {{ selected.pdf_path ? '重新导出 PDF' : '导出 PDF' }}
              </button>
              <a
                v-if="selected.pdf_path"
                :href="reportsApi.downloadUrl(selected.id)"
                target="_blank"
                class="btn-primary"
              >
                下载 PDF
              </a>
            </div>
          </div>
          <div
            class="markdown-body"
            v-html="renderedHtml"
          />
        </template>
      </div>
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
.report-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 20px;
  min-height: 600px;
}
.report-list {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  padding: 12px;
  overflow-y: auto;
  max-height: calc(100vh - 180px);
}
.loading,
.empty {
  text-align: center;
  padding: 40px 0;
  color: #94a3b8;
  font-size: 13px;
}
.report-item {
  padding: 14px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.2s;
}
.report-item:hover {
  background: #f8fafc;
}
.report-item.active {
  background: #eef2ff;
}
.report-item h4 {
  margin: 0 0 6px;
  font-size: 14px;
}
.report-item .meta {
  margin: 0;
  font-size: 12px;
  color: #64748b;
}
.report-item .time {
  margin: 4px 0 0;
  font-size: 11px;
  color: #94a3b8;
}
.badges {
  margin-top: 6px;
}
.badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}
.badge.pdf {
  background: #fee2e2;
  color: #dc2626;
}
.report-content {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  padding: 32px;
  overflow-y: auto;
  max-height: calc(100vh - 180px);
}
.empty-content {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
}
.content-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 16px;
  margin-bottom: 20px;
}
.content-toolbar h3 {
  margin: 0;
}
.content-toolbar > div {
  display: flex;
  gap: 8px;
}
.btn-outline {
  background: #fff;
  color: var(--primary);
  border: 1px solid var(--primary);
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}
.btn-primary {
  display: inline-block;
  background: var(--primary);
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  text-decoration: none;
}
.markdown-body {
  line-height: 1.8;
  font-size: 14px;
}
.markdown-body :deep(h1) {
  font-size: 22px;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 8px;
}
.markdown-body :deep(h2) {
  font-size: 18px;
  margin-top: 24px;
}
.markdown-body :deep(h4) {
  font-size: 15px;
}
.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 8px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: #f8fafc;
}
.markdown-body :deep(pre) {
  background: #1e293b;
  color: #e2e8f0;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
}
.markdown-body :deep(code) {
  font-family: Consolas, monospace;
  font-size: 13px;
}
.markdown-body :deep(img) {
  max-width: 100%;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}
</style>

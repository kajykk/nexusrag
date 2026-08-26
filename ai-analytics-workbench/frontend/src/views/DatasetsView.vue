<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useDatasetStore } from '@/stores/dataset'
import type { DatasetDetail } from '@/api/types'

const store = useDatasetStore()

const showUpload = ref(false)
const uploadForm = ref({ name: '', description: '' })
const uploadFile = ref<File | null>(null)
const uploading = ref(false)
const uploadError = ref('')

const detailVisible = ref(false)
const detailData = ref<DatasetDetail | null>(null)
const actionError = ref('')

onMounted(() => store.fetchList())

function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  uploadFile.value = target.files?.[0] || null
  if (uploadFile.value && !uploadForm.value.name) {
    uploadForm.value.name = uploadFile.value.name.replace(/\.[^.]+$/, '')
  }
}

async function doUpload() {
  if (!uploadFile.value || !uploadForm.value.name) {
    uploadError.value = '请填写名称并选择文件'
    return
  }
  uploading.value = true
  uploadError.value = ''
  try {
    await store.upload(uploadFile.value, uploadForm.value.name, uploadForm.value.description)
    showUpload.value = false
    uploadForm.value = { name: '', description: '' }
    uploadFile.value = null
  } catch (e) {
    uploadError.value = e instanceof Error ? e.message : String(e)
  } finally {
    uploading.value = false
  }
}

async function viewDetail(id: number) {
  actionError.value = ''
  try {
    detailData.value = await store.fetchDetail(id)
    detailVisible.value = true
  } catch (e) {
    actionError.value = `详情加载失败：${e instanceof Error ? e.message : String(e)}`
  }
}

async function removeDataset(id: number) {
  if (!confirm('确定删除该数据集？关联的分析任务也会被删除。')) return
  actionError.value = ''
  try {
    await store.remove(id)
  } catch (e) {
    // 只读遗留行（NULL 属主）删除会被后端拒绝为 404，这里给出可见反馈
    actionError.value = `删除失败：${e instanceof Error ? e.message : String(e)}`
  }
}
</script>

<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h2>数据集管理</h2>
        <p class="subtitle">
          上传 CSV / Excel 文件，自动入库 PostgreSQL
        </p>
      </div>
      <button
        class="btn-primary"
        @click="showUpload = true"
      >
        + 上传数据集
      </button>
    </header>

    <p
      v-if="actionError"
      class="error action-error"
      role="alert"
    >
      {{ actionError }}
    </p>

    <!-- 数据集列表 -->
    <div
      v-if="store.list.length === 0 && !store.loading"
      class="empty"
    >
      <p>暂无数据集，点击右上角上传</p>
    </div>

    <div
      v-else
      class="grid"
    >
      <div
        v-for="d in store.list"
        :key="d.id"
        class="card"
      >
        <div class="card-header">
          <span
            class="file-badge"
            :class="d.file_type"
          >{{ d.file_type }}</span>
          <h3>{{ d.name }}</h3>
        </div>
        <div class="card-meta">
          <span>📄 {{ d.original_filename }}</span>
          <span>📊 {{ d.row_count.toLocaleString() }} 行 × {{ d.column_count }} 列</span>
        </div>
        <div class="card-time">
          {{ d.created_at?.slice(0, 19).replace('T', ' ') }}
        </div>
        <div class="card-actions">
          <button
            class="btn-text"
            @click="viewDetail(d.id)"
          >
            查看详情
          </button>
          <button
            class="btn-text danger"
            @click="removeDataset(d.id)"
          >
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- 上传弹窗 -->
    <div
      v-if="showUpload"
      class="modal-mask"
      @click.self="showUpload = false"
    >
      <div class="modal">
        <h3>上传数据集</h3>
        <div class="form-group">
          <label>数据集名称</label>
          <input
            v-model="uploadForm.name"
            placeholder="给数据集起个名字"
          >
        </div>
        <div class="form-group">
          <label>描述（可选）</label>
          <input
            v-model="uploadForm.description"
            placeholder="数据集说明"
          >
        </div>
        <div class="form-group">
          <label>选择文件（CSV / XLSX / XLS）</label>
          <input
            type="file"
            accept=".csv,.xlsx,.xls"
            @change="handleFileChange"
          >
        </div>
        <p
          v-if="uploadError"
          class="error"
        >
          {{ uploadError }}
        </p>
        <div class="modal-actions">
          <button
            class="btn-text"
            @click="showUpload = false"
          >
            取消
          </button>
          <button
            class="btn-primary"
            :disabled="uploading"
            @click="doUpload"
          >
            {{ uploading ? '上传中...' : '确认上传' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div
      v-if="detailVisible && detailData"
      class="modal-mask"
      @click.self="detailVisible = false"
    >
      <div class="modal modal-lg">
        <h3>{{ detailData.name }}</h3>
        <p class="subtitle">
          {{ detailData.row_count }} 行 × {{ detailData.column_count }} 列 ·
          {{ detailData.file_type }}
        </p>
        <h4>列信息</h4>
        <table class="schema-table">
          <thead>
            <tr>
              <th>列名</th>
              <th>类型</th>
              <th>空值</th>
              <th>唯一值</th>
              <th>样例</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in detailData.columns_schema"
              :key="c.name"
            >
              <td>
                <code>{{ c.name }}</code>
              </td>
              <td>{{ c.dtype }}</td>
              <td>{{ c.null_count }}</td>
              <td>{{ c.unique_count }}</td>
              <td class="sample">
                {{ c.sample.join(', ') }}
              </td>
            </tr>
          </tbody>
        </table>
        <h4>数据预览（前 5 行）</h4>
        <div class="preview-wrap">
          <table class="preview-table">
            <thead>
              <tr>
                <th
                  v-for="key in Object.keys(detailData.preview[0] || {})"
                  :key="key"
                >
                  {{ key }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, i) in detailData.preview"
                :key="i"
              >
                <td
                  v-for="key in Object.keys(detailData.preview[0] || {})"
                  :key="key"
                >
                  {{ row[key] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="modal-actions">
          <button
            class="btn-primary"
            @click="detailVisible = false"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
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
.empty {
  text-align: center;
  padding: 80px 0;
  color: #94a3b8;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.card {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  border: 1px solid #e2e8f0;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.card-header h3 {
  margin: 0;
  font-size: 16px;
}
.file-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #e0e7ff;
  color: #4f46e5;
  text-transform: uppercase;
  font-weight: 600;
}
.card-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #64748b;
}
.card-time {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 8px;
}
.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  border-top: 1px solid #f1f5f9;
  padding-top: 12px;
}
.btn-primary {
  background: var(--primary);
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: opacity 0.2s;
}
.btn-primary:hover {
  opacity: 0.9;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-text {
  background: none;
  border: none;
  color: var(--primary);
  cursor: pointer;
  font-size: 13px;
  padding: 4px 8px;
}
.btn-text.danger {
  color: #ef4444;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
}
.modal {
  background: #fff;
  border-radius: 12px;
  padding: 28px;
  width: 480px;
  max-width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}
.modal-lg {
  width: 880px;
}
.modal h3 {
  margin: 0 0 8px;
}
.modal h4 {
  margin: 20px 0 8px;
  font-size: 14px;
  color: #475569;
}
.form-group {
  margin-bottom: 16px;
}
.form-group label {
  display: block;
  font-size: 13px;
  color: #64748b;
  margin-bottom: 6px;
}
.form-group input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
}
.error {
  color: #ef4444;
  font-size: 13px;
}
.action-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 16px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}
.schema-table,
.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.schema-table th,
.preview-table th {
  background: #f8fafc;
  padding: 8px;
  text-align: left;
  border-bottom: 2px solid #e2e8f0;
}
.schema-table td,
.preview-table td {
  padding: 8px;
  border-bottom: 1px solid #f1f5f9;
}
.schema-table code {
  background: #f1f5f9;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.sample {
  max-width: 240px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.preview-wrap {
  overflow-x: auto;
}
</style>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
import { docApi, type Doc } from '@/api/documents'
import {
  ArrowLeft, Upload, FileText, Trash2, MessageSquare,
  Loader2, File, CheckCircle2, AlertCircle, Clock, ChevronRight,
} from 'lucide-vue-next'

const props = defineProps<{ id: string }>()
const auth = useAuthStore()
const kbStore = useKbStore()
const router = useRouter()

const docs = ref<Doc[]>([])
const loading = ref(false)
const uploading = ref(false)
const dragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
let pollTimer: ReturnType<typeof setTimeout> | null = null

const sortedDocs = computed(() => {
  return [...docs.value].sort((a, b) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
})

const stats = computed(() => {
  const total = docs.value.length
  const ready = docs.value.filter((d) => d.status === 'ready').length
  const processing = docs.value.filter((d) => d.status === 'processing' || d.status === 'pending').length
  const failed = docs.value.filter((d) => d.status === 'failed').length
  const chunks = docs.value.reduce((s, d) => s + (d.chunk_count || 0), 0)
  return { total, ready, processing, failed, chunks }
})

async function fetchDocs() {
  loading.value = true
  try {
    docs.value = await docApi.list(props.id)
  } finally {
    loading.value = false
  }
}

async function pollStatus() {
  // 轮询处理中的文档状态
  const pending = docs.value.filter((d) => d.status === 'processing' || d.status === 'pending')
  for (const doc of pending) {
    try {
      const updated = await docApi.status(props.id, doc.id)
      Object.assign(doc, updated)
    } catch {
      // ignore
    }
  }
  if (pending.length > 0) {
    schedulePoll()
  }
}

function schedulePoll(delay = 2000) {
  // 避免重复轮询循环叠加
  if (pollTimer !== null) clearTimeout(pollTimer)
  pollTimer = setTimeout(() => {
    pollTimer = null
    pollStatus()
  }, delay)
}

onUnmounted(() => {
  if (pollTimer !== null) clearTimeout(pollTimer)
  pollTimer = null
})

async function onFiles(files: FileList | File[]) {
  if (!files || (files as FileList).length === 0) return
  uploading.value = true
  try {
    const arr = Array.from(files as FileList)
    const newDocs = await docApi.upload(props.id, arr)
    docs.value.push(...newDocs)
    schedulePoll(1000)
  } catch (e: any) {
    alert(e.response?.data?.error || e.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

function onDrop(e: DragEvent) {
  dragOver.value = false
  if (e.dataTransfer?.files) {
    onFiles(e.dataTransfer.files)
  }
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) onFiles(input.files)
  input.value = ''
}

async function removeDoc(docId: string) {
  if (!confirm('确定删除该文档？相关向量和索引也会一并删除。')) return
  try {
    await docApi.delete(props.id, docId)
    docs.value = docs.value.filter((d) => d.id !== docId)
  } catch (e: any) {
    alert(e.response?.data?.error || e.message || '删除失败')
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function statusBadge(status: Doc['status']) {
  switch (status) {
    case 'ready': return { cls: 'badge-success', icon: CheckCircle2, text: '就绪' }
    case 'processing': return { cls: 'badge-warn', icon: Loader2, text: '处理中' }
    case 'pending': return { cls: 'badge-warn', icon: Clock, text: '排队中' }
    case 'failed': return { cls: 'badge-error', icon: AlertCircle, text: '失败' }
  }
}

onMounted(async () => {
  if (!auth.token) auth.restore()
  try {
    await kbStore.fetchOne(props.id)
  } catch {
    router.push('/dashboard')
    return
  }
  await fetchDocs()
  schedulePoll(1000)
})
</script>

<template>
  <div class="min-h-screen bg-bg-base text-text-primary">
    <div class="absolute top-0 left-0 right-0 h-64 bg-radial-glow pointer-events-none opacity-30"></div>

    <header class="relative border-b border-border-subtle/50 backdrop-blur-md sticky top-0 z-20 bg-bg-base/80">
      <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <RouterLink to="/dashboard" class="flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors">
          <ArrowLeft class="w-4 h-4" />
          <span class="text-sm">返回工作台</span>
        </RouterLink>
        <RouterLink :to="`/chat/${id}`" class="btn-primary text-sm">
          <MessageSquare class="w-4 h-4" />
          开始对话
        </RouterLink>
      </div>
    </header>

    <main class="relative max-w-7xl mx-auto px-6 py-10">
      <!-- 知识库信息 -->
      <div class="mb-8">
        <div class="text-accent-cyan text-xs font-mono mb-2">/ KNOWLEDGE BASE</div>
        <h1 class="font-display font-bold text-3xl mb-2">{{ kbStore.current?.name || '加载中...' }}</h1>
        <p class="text-text-secondary">{{ kbStore.current?.description || '暂无描述' }}</p>
      </div>

      <!-- 统计卡片 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div class="glass-card p-4">
          <div class="text-xs text-text-muted mb-1">总文档数</div>
          <div class="font-display font-bold text-2xl text-accent-cyan">{{ stats.total }}</div>
        </div>
        <div class="glass-card p-4">
          <div class="text-xs text-text-muted mb-1">已就绪</div>
          <div class="font-display font-bold text-2xl text-emerald-400">{{ stats.ready }}</div>
        </div>
        <div class="glass-card p-4">
          <div class="text-xs text-text-muted mb-1">处理中</div>
          <div class="font-display font-bold text-2xl text-amber-400">{{ stats.processing }}</div>
        </div>
        <div class="glass-card p-4">
          <div class="text-xs text-text-muted mb-1">分块总数</div>
          <div class="font-display font-bold text-2xl text-accent-violet">{{ stats.chunks }}</div>
        </div>
      </div>

      <!-- 上传区 -->
      <div
        class="glass-card p-10 mb-8 cursor-pointer transition-all text-center"
        :class="dragOver ? 'border-accent-cyan scale-[1.01]' : 'hover:border-accent-cyan/40'"
        @dragover.prevent="dragOver = true"
        @dragleave.prevent="dragOver = false"
        @drop.prevent="onDrop"
        @click="fileInput?.click()"
      >
        <input
          ref="fileInput"
          type="file"
          multiple
          accept=".pdf,.docx,.doc,.md,.markdown,.txt"
          class="hidden"
          @change="onFileChange"
        />
        <div class="w-14 h-14 rounded-full bg-accent-cyan/10 mx-auto flex items-center justify-center mb-4">
          <Upload v-if="!uploading" class="w-6 h-6 text-accent-cyan" />
          <Loader2 v-else class="w-6 h-6 text-accent-cyan animate-spin" />
        </div>
        <div class="font-display font-semibold text-lg mb-1">
          {{ uploading ? '上传中...' : '拖拽文件到此处或点击上传' }}
        </div>
        <div class="text-sm text-text-secondary">
          支持 PDF / Word / Markdown / TXT，单个文件最大 50MB
        </div>
      </div>

      <!-- 文档列表 -->
      <div class="glass-card">
        <div class="px-6 py-4 border-b border-border-subtle">
          <h3 class="font-display font-semibold">文档列表</h3>
        </div>

        <div v-if="loading" class="p-12 text-center text-text-secondary">
          <Loader2 class="w-5 h-5 animate-spin inline mr-2" />
          加载中...
        </div>

        <div v-else-if="sortedDocs.length === 0" class="p-12 text-center text-text-muted">
          <FileText class="w-10 h-10 mx-auto mb-3 opacity-50" />
          还没有文档，上传一个开始体验
        </div>

        <div v-else class="divide-y divide-border-subtle">
          <div
            v-for="doc in sortedDocs"
            :key="doc.id"
            class="px-6 py-4 flex items-center gap-4 hover:bg-bg-hover transition-colors group"
          >
            <div class="w-10 h-10 rounded-lg bg-bg-elevate flex items-center justify-center shrink-0">
              <File class="w-5 h-5 text-accent-cyan" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-medium truncate">{{ doc.name }}</div>
              <div class="text-xs text-text-muted mt-0.5 flex items-center gap-3">
                <span>{{ formatSize(doc.file_size) }}</span>
                <span>·</span>
                <span>{{ doc.file_type.toUpperCase() }}</span>
                <span v-if="doc.chunk_count > 0">·</span>
                <span v-if="doc.chunk_count > 0">{{ doc.chunk_count }} 个分块</span>
                <span>·</span>
                <span>{{ new Date(doc.created_at).toLocaleString('zh-CN') }}</span>
              </div>
              <div v-if="doc.error" class="text-xs text-red-400 mt-1">{{ doc.error }}</div>
            </div>
            <span :class="statusBadge(doc.status)?.cls" class="badge">
              <component :is="statusBadge(doc.status)?.icon" class="w-3 h-3" :class="{ 'animate-spin': doc.status === 'processing' }" />
              {{ statusBadge(doc.status)?.text }}
            </span>
            <button
              class="opacity-0 group-hover:opacity-100 p-2 rounded-md hover:bg-red-500/10 text-text-muted hover:text-red-400 transition-all"
              @click="removeDoc(doc.id)"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <!-- 引导开始对话 -->
      <div v-if="stats.ready > 0" class="mt-8 text-center">
        <RouterLink :to="`/chat/${id}`" class="btn-primary text-base px-6 py-3">
          <MessageSquare class="w-5 h-5" />
          开始与知识库对话
          <ChevronRight class="w-4 h-4" />
        </RouterLink>
      </div>
    </main>
  </div>
</template>

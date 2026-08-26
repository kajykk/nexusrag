<script setup lang="ts">
import { onMounted, ref, nextTick, computed } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { chatApi, type ChatMessage } from '@/api/chat'
import { kbApi, type KnowledgeBase } from '@/api/kb'
import ChatMarkdown from '@/components/ChatMarkdown.vue'
import type { Citation } from '@/api/types'
import {
  Sparkles, ArrowLeft, Send, Plus, Trash2, MessageSquare,
  Loader2, Brain, Zap, BookOpen, ChevronDown, Quote, X,
} from 'lucide-vue-next'

const props = defineProps<{ kbId: string; sessionId?: string }>()
const auth = useAuthStore()
const router = useRouter()

interface Msg {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  status?: 'streaming' | 'done'
  statusMsg?: string
}

const kb = ref<KnowledgeBase | null>(null)
const sessions = ref<{ id: string; title: string; mode: string; created_at: string }[]>([])
const currentSessionId = ref<string | null>(null)
const messages = ref<Msg[]>([])
const input = ref('')
const mode = ref<'normal' | 'agent'>('normal')
const sending = ref(false)
const loadingHistory = ref(false)
const showCitations = ref(false)
const activeCitations = ref<Citation[]>([])
const messagesContainer = ref<HTMLElement | null>(null)

const status = computed(() => {
  if (!kb.value) return ''
  return `${kb.value.name}`
})

const canSend = computed(() => input.value.trim().length > 0 && !sending.value)

// 新消息时滚动到底部
async function scrollToBottom() {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 流式输出期间按帧合并滚动，避免每个 token 触发一次布局计算
let scrollScheduled = false
function scheduleScroll() {
  if (scrollScheduled) return
  scrollScheduled = true
  requestAnimationFrame(() => {
    scrollScheduled = false
    void scrollToBottom()
  })
}

async function fetchSessions() {
  try {
    sessions.value = await chatApi.listSessions(props.kbId)
  } catch {
    // ignore
  }
}

async function selectSession(sid: string) {
  currentSessionId.value = sid
  loadingHistory.value = true
  messages.value = []
  try {
    const history = await chatApi.getMessages(props.kbId, sid)
    messages.value = history.map((m: ChatMessage) => ({
      id: m.id,
      role: m.role as 'user' | 'assistant',
      content: m.content,
      citations: m.citations,
      status: 'done' as const,
    }))
    await scrollToBottom()
  } finally {
    loadingHistory.value = false
  }
  router.replace(`/chat/${props.kbId}/${sid}`)
}

async function newSession() {
  currentSessionId.value = null
  messages.value = []
  router.replace(`/chat/${props.kbId}`)
}

async function send() {
  if (!canSend.value) return
  const content = input.value.trim()
  input.value = ''
  sending.value = true

  // 创建会话（如未选中）
  if (!currentSessionId.value) {
    try {
      const s = await chatApi.createSession(props.kbId, {
        title: content.slice(0, 40),
        mode: mode.value,
      })
      currentSessionId.value = s.id
      router.replace(`/chat/${props.kbId}/${s.id}`)
      fetchSessions()
    } catch (e: any) {
      alert(e.response?.data?.error || e.message || '创建会话失败')
      sending.value = false
      return
    }
  }

  // 添加用户消息
  messages.value.push({
    id: `u_${Date.now()}`,
    role: 'user',
    content,
    status: 'done',
  })

  // 添加空的 assistant 消息（流式）
  const assistantMsg: Msg = {
    id: `a_${Date.now()}`,
    role: 'assistant',
    content: '',
    status: 'streaming',
    statusMsg: '正在准备...',
  }
  messages.value.push(assistantMsg)
  await scrollToBottom()

  try {
    await chatApi.sendMessage(
      props.kbId,
      currentSessionId.value!,
      content,
      mode.value,
      (chunk) => {
        if (chunk.type === 'token') {
          assistantMsg.content += chunk.data.content || ''
          scheduleScroll()
        } else if (chunk.type === 'citation') {
          assistantMsg.citations = chunk.data.citations
        } else if (chunk.type === 'status') {
          assistantMsg.statusMsg = chunk.data.status
        } else if (chunk.type === 'error') {
          assistantMsg.statusMsg = `错误：${chunk.data.error}`
        } else if (chunk.type === 'done') {
          assistantMsg.status = 'done'
        }
      },
    )
    assistantMsg.status = 'done'
  } catch (e: any) {
    assistantMsg.content = `**发生错误**\n\n${e.message}\n\n请检查后端服务与 LLM 配置。`
    assistantMsg.status = 'done'
  } finally {
    sending.value = false
    fetchSessions()
  }
}

function onInputKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function showCitationPanel(citations?: Citation[]) {
  if (!citations || citations.length === 0) return
  activeCitations.value = citations
  showCitations.value = true
}

async function deleteSession(sid: string) {
  if (!confirm('删除该会话？')) return
  await chatApi.deleteSession(props.kbId, sid)
  sessions.value = sessions.value.filter((s) => s.id !== sid)
  if (currentSessionId.value === sid) newSession()
}

onMounted(async () => {
  if (!auth.token) auth.restore()
  try {
    kb.value = await kbApi.get(props.kbId)
  } catch {
    router.push('/dashboard')
    return
  }
  await fetchSessions()
  if (props.sessionId) {
    selectSession(props.sessionId)
  }
})
</script>

<template>
  <div class="h-screen bg-bg-base text-text-primary flex overflow-hidden">
    <!-- 左侧：会话列表 -->
    <aside class="w-72 border-r border-border-subtle flex flex-col bg-bg-card/50">
      <div class="p-4 border-b border-border-subtle">
        <RouterLink to="/dashboard" class="flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors text-sm mb-3">
          <ArrowLeft class="w-4 h-4" />
          返回工作台
        </RouterLink>
        <div class="flex items-center gap-2">
          <div class="w-9 h-9 rounded-lg bg-gradient-cv flex items-center justify-center shrink-0">
            <Sparkles class="w-4 h-4 text-white" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="font-display font-semibold text-sm truncate">{{ status }}</div>
            <div class="text-xs text-text-muted">知识库对话</div>
          </div>
        </div>
      </div>

      <div class="p-3">
        <button class="btn-ghost w-full justify-center text-sm" @click="newSession">
          <Plus class="w-4 h-4" />
          新对话
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-2 pb-2">
        <div class="text-xs text-text-muted px-2 py-2">历史会话</div>
        <div v-if="sessions.length === 0" class="px-3 py-6 text-center text-text-muted text-sm">
          暂无历史
        </div>
        <button
          v-for="s in sessions"
          :key="s.id"
          class="group w-full text-left px-3 py-2 rounded-lg mb-1 transition-colors flex items-center gap-2"
          :class="currentSessionId === s.id ? 'bg-bg-elevate text-text-primary' : 'hover:bg-bg-hover text-text-secondary'"
          @click="selectSession(s.id)"
        >
          <MessageSquare class="w-4 h-4 shrink-0 opacity-50" />
          <div class="flex-1 min-w-0">
            <div class="text-sm truncate">{{ s.title || '新对话' }}</div>
            <div class="text-xs text-text-muted">{{ new Date(s.created_at).toLocaleDateString('zh-CN') }}</div>
          </div>
          <span v-if="s.mode === 'agent'" class="badge badge-violet text-[10px]">Agent</span>
          <span
            class="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 hover:text-red-400 transition-all"
            @click.stop="deleteSession(s.id)"
          >
            <Trash2 class="w-3 h-3" />
          </span>
        </button>
      </div>
    </aside>

    <!-- 右侧：对话主区 -->
    <main class="flex-1 flex flex-col min-w-0 relative">
      <!-- 顶栏：模式切换 -->
      <header class="border-b border-border-subtle px-6 py-3 flex items-center justify-between bg-bg-base/80 backdrop-blur">
        <div class="flex items-center gap-3">
          <div class="flex p-1 rounded-lg bg-bg-elevate">
            <button
              class="px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5"
              :class="mode === 'normal' ? 'bg-bg-card text-accent-cyan shadow' : 'text-text-muted hover:text-text-primary'"
              @click="mode = 'normal'"
            >
              <Zap class="w-3.5 h-3.5" />
              普通 RAG
            </button>
            <button
              class="px-3 py-1.5 rounded-md text-xs font-medium transition-all flex items-center gap-1.5"
              :class="mode === 'agent' ? 'bg-bg-card text-accent-violet shadow' : 'text-text-muted hover:text-text-primary'"
              @click="mode = 'agent'"
            >
              <Brain class="w-3.5 h-3.5" />
              Agent 深度研究
            </button>
          </div>
        </div>
        <RouterLink :to="`/kb/${kbId}`" class="text-sm text-text-secondary hover:text-text-primary flex items-center gap-2">
          <BookOpen class="w-4 h-4" />
          管理文档
        </RouterLink>
      </header>

      <!-- 消息列表 -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto">
        <div class="max-w-3xl mx-auto px-6 py-8">
          <!-- 空状态 -->
          <div v-if="messages.length === 0 && !loadingHistory" class="text-center pt-20">
            <div class="w-16 h-16 rounded-full bg-gradient-cv/20 mx-auto flex items-center justify-center mb-4">
              <Sparkles class="w-7 h-7 text-accent-cyan" />
            </div>
            <h2 class="font-display font-bold text-2xl mb-2">
              {{ mode === 'agent' ? 'Agent 深度研究模式' : '开始与知识库对话' }}
            </h2>
            <p class="text-text-secondary text-sm max-w-md mx-auto mb-8">
              {{ mode === 'agent'
                ? 'Agent 会自动拆解问题、多轮检索、反思评估，最终生成结构化研究报告。'
                : '基于检索增强生成（RAG）技术，AI 会从你的文档中检索相关内容并精准回答。' }}
            </p>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
              <button
                v-for="q in ['总结一下这个知识库的核心内容', '有哪些关键信息？请列出', '帮我对比文档中的不同观点', '基于文档给出建议']"
                :key="q"
                class="glass-card p-3 text-left text-sm hover:border-accent-cyan/40 transition-colors text-text-secondary hover:text-text-primary"
                @click="input = q; send()"
              >
                {{ q }}
              </button>
            </div>
          </div>

          <!-- 加载中 -->
          <div v-else-if="loadingHistory" class="text-center py-20 text-text-secondary">
            <Loader2 class="w-6 h-6 animate-spin inline" />
          </div>

          <!-- 消息 -->
          <div v-else class="space-y-6">
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="flex gap-4 animate-fade-in"
              :class="msg.role === 'user' ? 'flex-row-reverse' : ''"
            >
              <!-- 头像 -->
              <div
                class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                :class="msg.role === 'user' ? 'bg-bg-elevate' : 'bg-gradient-cv'"
              >
                <Sparkles v-if="msg.role === 'assistant'" class="w-4 h-4 text-white" />
                <span v-else class="text-sm font-bold">{{ auth.user?.name?.[0] || 'U' }}</span>
              </div>

              <!-- 消息内容 -->
              <div class="flex-1 min-w-0" :class="msg.role === 'user' ? 'text-right' : ''">
                <div class="text-xs text-text-muted mb-1">
                  {{ msg.role === 'user' ? (auth.user?.name || '我') : 'NexusRAG' }}
                </div>

                <!-- 用户消息 -->
                <div v-if="msg.role === 'user'" class="inline-block bg-bg-elevate rounded-2xl rounded-tr-sm px-4 py-2.5 text-left">
                  <div class="whitespace-pre-wrap">{{ msg.content }}</div>
                </div>

                <!-- 助手消息 -->
                <div v-else class="text-left">
                  <!-- 状态提示 -->
                  <div v-if="msg.status === 'streaming' && msg.statusMsg" class="mb-2 flex items-center gap-2 text-sm text-accent-cyan">
                    <Loader2 class="w-3.5 h-3.5 animate-spin" />
                    <span class="text-text-secondary whitespace-pre-wrap">{{ msg.statusMsg }}</span>
                  </div>

                  <!-- 内容 -->
                  <ChatMarkdown
                    v-if="msg.content"
                    :content="msg.content"
                    :citations="msg.citations"
                  />

                  <!-- 引用 -->
                  <div v-if="msg.citations && msg.citations.length > 0 && msg.status === 'done'" class="mt-4">
                    <button
                      class="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg bg-bg-elevate border border-border-subtle hover:border-accent-cyan/40 text-text-secondary hover:text-text-primary transition-colors"
                      @click="showCitationPanel(msg.citations)"
                    >
                      <Quote class="w-3.5 h-3.5" />
                      {{ msg.citations.length }} 个引用来源
                      <ChevronDown class="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入框 -->
      <footer class="border-t border-border-subtle bg-bg-base/80 backdrop-blur">
        <div class="max-w-3xl mx-auto px-6 py-4">
          <div class="relative">
            <textarea
              v-model="input"
              :placeholder="mode === 'agent' ? '描述你的研究问题，Agent 会多轮检索并生成报告...' : '提出你的问题...'"
              rows="2"
              class="input-field resize-none pr-24"
              :disabled="sending"
              @keydown="onInputKeydown"
            />
            <button
              :disabled="!canSend"
              class="absolute right-2 bottom-2 px-3 py-2 rounded-lg bg-gradient-cv text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-accent-cyan/30 transition-all flex items-center gap-1.5"
              @click="send"
            >
              <Send v-if="!sending" class="w-3.5 h-3.5" />
              <Loader2 v-else class="w-3.5 h-3.5 animate-spin" />
              {{ sending ? '生成中' : '发送' }}
            </button>
          </div>
          <div class="text-xs text-text-muted mt-2 flex items-center gap-2">
            <span>Enter 发送 · Shift+Enter 换行</span>
            <span>·</span>
            <span v-if="mode === 'agent'" class="text-accent-violet">Agent 模式启用</span>
          </div>
        </div>
      </footer>
    </main>

    <!-- 引用面板（侧滑） -->
    <transition name="slide">
      <aside v-if="showCitations" class="absolute right-0 top-0 bottom-0 w-96 bg-bg-card border-l border-border-subtle z-30 overflow-y-auto">
        <div class="sticky top-0 bg-bg-card/95 backdrop-blur border-b border-border-subtle px-5 py-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <Quote class="w-4 h-4 text-accent-cyan" />
            <h3 class="font-display font-semibold">引用来源</h3>
            <span class="badge badge-cyan">{{ activeCitations.length }}</span>
          </div>
          <button class="p-1.5 rounded hover:bg-bg-hover" @click="showCitations = false">
            <X class="w-4 h-4" />
          </button>
        </div>
        <div class="p-5 space-y-4">
          <div v-for="c in activeCitations" :key="c.id" class="glass-card p-4">
            <div class="flex items-center justify-between mb-2">
              <div class="flex items-center gap-2">
                <div class="w-7 h-7 rounded-md bg-accent-cyan/10 text-accent-cyan font-mono font-bold text-sm flex items-center justify-center">
                  {{ c.id }}
                </div>
                <div class="text-sm font-medium truncate">{{ c.docName }}</div>
              </div>
              <div v-if="c.page" class="text-xs text-text-muted">P. {{ c.page }}</div>
            </div>
            <div class="text-sm text-text-secondary leading-relaxed border-l-2 border-accent-cyan/30 pl-3 italic">
              {{ c.content }}
            </div>
            <div class="text-xs text-text-muted mt-2">相关度：{{ (c.score * 100).toFixed(1) }}%</div>
          </div>
        </div>
      </aside>
    </transition>
  </div>
</template>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>

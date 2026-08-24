<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useKbStore } from '@/stores/kb'
import { Sparkles, Plus, BookOpen, MessageSquare, Trash2, ArrowRight, Loader2 } from 'lucide-vue-next'

const auth = useAuthStore()
const kbStore = useKbStore()
const router = useRouter()

const showCreate = ref(false)
const newName = ref('')
const newDesc = ref('')
const creating = ref(false)

async function createKb() {
  if (!newName.value.trim()) return
  creating.value = true
  try {
    const kb = await kbStore.create(newName.value.trim(), newDesc.value.trim())
    showCreate.value = false
    newName.value = ''
    newDesc.value = ''
    router.push(`/kb/${kb.id}`)
  } finally {
    creating.value = false
  }
}

function logout() {
  auth.logout()
  router.push('/')
}

onMounted(async () => {
  if (!auth.token) auth.restore()
  if (auth.token) await kbStore.fetchList()
})
</script>

<template>
  <div class="min-h-screen bg-bg-base text-text-primary">
    <div class="absolute top-0 left-0 right-0 h-64 bg-radial-glow pointer-events-none opacity-50"></div>

    <!-- 顶栏 -->
    <header class="relative border-b border-border-subtle/50 backdrop-blur-md sticky top-0 z-20 bg-bg-base/80">
      <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <RouterLink to="/" class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-gradient-cv flex items-center justify-center">
            <Sparkles class="w-5 h-5 text-white" />
          </div>
          <div>
            <div class="font-display font-bold">NexusRAG</div>
            <div class="text-xs text-text-muted -mt-1">工作台</div>
          </div>
        </RouterLink>
        <div class="flex items-center gap-4">
          <div class="text-sm text-text-secondary hidden md:block">
            你好，<span class="text-text-primary font-medium">{{ auth.user?.name }}</span>
          </div>
          <button @click="logout" class="btn-ghost text-sm">退出</button>
        </div>
      </div>
    </header>

    <main class="relative max-w-7xl mx-auto px-6 py-10">
      <!-- 标题 -->
      <div class="flex items-end justify-between mb-8">
        <div>
          <div class="text-accent-cyan text-xs font-mono mb-2">/ DASHBOARD</div>
          <h1 class="font-display font-bold text-3xl">我的知识库</h1>
          <p class="text-text-secondary mt-1">管理你的知识库，开始与文档对话</p>
        </div>
        <button @click="showCreate = true" class="btn-primary">
          <Plus class="w-4 h-4" />
          新建知识库
        </button>
      </div>

      <!-- 加载中 -->
      <div v-if="kbStore.loading" class="flex items-center justify-center py-20 text-text-secondary">
        <Loader2 class="w-5 h-5 animate-spin mr-2" />
        加载中...
      </div>

      <!-- 空状态 -->
      <div v-else-if="kbStore.list.length === 0" class="glass-card p-12 text-center">
        <div class="w-16 h-16 rounded-full bg-bg-elevate mx-auto flex items-center justify-center mb-4">
          <BookOpen class="w-8 h-8 text-text-muted" />
        </div>
        <h3 class="font-display font-semibold text-xl mb-2">还没有知识库</h3>
        <p class="text-text-secondary text-sm mb-6">创建第一个知识库，上传文档开始体验</p>
        <button @click="showCreate = true" class="btn-primary">
          <Plus class="w-4 h-4" />
          创建知识库
        </button>
      </div>

      <!-- 知识库列表 -->
      <div v-else class="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
        <div
          v-for="kb in kbStore.list"
          :key="kb.id"
          class="glass-card p-5 hover:border-accent-cyan/40 transition-all hover:-translate-y-1 group"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="w-11 h-11 rounded-lg bg-gradient-cv/20 flex items-center justify-center">
              <BookOpen class="w-5 h-5 text-accent-cyan" />
            </div>
            <button
              @click.stop="kbStore.remove(kb.id)"
              class="opacity-0 group-hover:opacity-100 transition-opacity p-2 rounded-md hover:bg-red-500/10 text-text-muted hover:text-red-400"
              title="删除"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
          <h3 class="font-display font-semibold text-lg mb-1 truncate">{{ kb.name }}</h3>
          <p class="text-sm text-text-secondary line-clamp-2 min-h-[2.5rem]">
            {{ kb.description || '暂无描述' }}
          </p>
          <div class="flex items-center gap-3 mt-4 text-xs text-text-muted">
            <span class="badge badge-cyan">{{ kb.document_count }} 文档</span>
            <span>{{ new Date(kb.created_at).toLocaleDateString('zh-CN') }}</span>
          </div>
          <div class="flex gap-2 mt-4 pt-4 border-t border-border-subtle">
            <RouterLink :to="`/kb/${kb.id}`" class="btn-ghost flex-1 text-sm justify-center">
              管理文档
            </RouterLink>
            <RouterLink :to="`/chat/${kb.id}`" class="btn-primary flex-1 text-sm justify-center">
              <MessageSquare class="w-4 h-4" />
              对话
              <ArrowRight class="w-3 h-3" />
            </RouterLink>
          </div>
        </div>
      </div>
    </main>

    <!-- 创建知识库 Modal -->
    <div v-if="showCreate" class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" @click.self="showCreate = false">
      <div class="glass-card p-6 w-full max-w-md animate-slide-up">
        <h3 class="font-display font-bold text-xl mb-4">新建知识库</h3>
        <div class="space-y-4">
          <div>
            <label class="block text-xs text-text-secondary mb-1.5">名称</label>
            <input v-model="newName" type="text" placeholder="例如：技术文档库" class="input-field" />
          </div>
          <div>
            <label class="block text-xs text-text-secondary mb-1.5">描述（可选）</label>
            <textarea v-model="newDesc" rows="3" placeholder="知识库用途说明..." class="input-field resize-none"></textarea>
          </div>
          <div class="flex gap-3 pt-2">
            <button @click="showCreate = false" class="btn-ghost flex-1 justify-center">取消</button>
            <button @click="createKb" :disabled="creating || !newName.trim()" class="btn-primary flex-1 justify-center disabled:opacity-50">
              {{ creating ? '创建中...' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { Sparkles, Mail, Lock, User, ArrowRight, Zap } from 'lucide-vue-next'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const mode = ref<'login' | 'register'>('login')
const email = ref('')
const password = ref('')
const name = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(email.value, password.value)
    } else {
      await auth.register(email.value, password.value, name.value)
    }
    const redirect = (route.query.redirect as string) || '/dashboard'
    router.push(redirect)
  } catch (e: any) {
    error.value = e.response?.data?.error || e.message || '操作失败'
  } finally {
    loading.value = false
  }
}

async function demoLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.demoLogin()
    router.push('/dashboard')
  } catch (e: any) {
    error.value = e.response?.data?.error || e.message || '演示登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-bg-base text-text-primary relative overflow-hidden flex items-center justify-center px-4">
    <!-- 背景 -->
    <div class="absolute inset-0 bg-grid-pattern bg-grid-lg opacity-40 pointer-events-none"></div>
    <div class="absolute top-1/4 left-1/3 w-[500px] h-[500px] bg-radial-glow rounded-full animate-pulse-glow pointer-events-none"></div>

    <div class="relative z-10 w-full max-w-md">
      <RouterLink to="/" class="flex items-center justify-center gap-3 mb-8 group">
        <div class="w-10 h-10 rounded-lg bg-gradient-cv flex items-center justify-center group-hover:scale-110 transition-transform">
          <Sparkles class="w-5 h-5 text-white" />
        </div>
        <div class="text-left">
          <div class="font-display font-bold text-xl">NexusRAG</div>
          <div class="text-xs text-text-muted -mt-0.5">智能知识库</div>
        </div>
      </RouterLink>

      <div class="glass-card p-8 animate-slide-up">
        <!-- 模式切换 -->
        <div class="flex p-1 mb-6 rounded-lg bg-bg-elevate">
          <button
            @click="mode = 'login'"
            class="flex-1 py-2 rounded-md text-sm font-medium transition-all"
            :class="mode === 'login' ? 'bg-bg-card text-text-primary shadow' : 'text-text-muted'"
          >
            登录
          </button>
          <button
            @click="mode = 'register'"
            class="flex-1 py-2 rounded-md text-sm font-medium transition-all"
            :class="mode === 'register' ? 'bg-bg-card text-text-primary shadow' : 'text-text-muted'"
          >
            注册
          </button>
        </div>

        <h2 class="font-display text-2xl font-bold mb-2">
          {{ mode === 'login' ? '欢迎回来' : '创建账号' }}
        </h2>
        <p class="text-text-secondary text-sm mb-6">
          {{ mode === 'login' ? '登录以使用你的知识库' : '注册后即可创建专属知识库' }}
        </p>

        <form @submit.prevent="submit" class="space-y-4">
          <div v-if="mode === 'register'">
            <label class="block text-xs text-text-secondary mb-1.5">昵称</label>
            <div class="relative">
              <User class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input v-model="name" type="text" required placeholder="你的名字" class="input-field pl-10" />
            </div>
          </div>

          <div>
            <label class="block text-xs text-text-secondary mb-1.5">邮箱</label>
            <div class="relative">
              <Mail class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input v-model="email" type="email" required placeholder="you@example.com" class="input-field pl-10" />
            </div>
          </div>

          <div>
            <label class="block text-xs text-text-secondary mb-1.5">密码</label>
            <div class="relative">
              <Lock class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input v-model="password" type="password" required placeholder="••••••••" class="input-field pl-10" minlength="6" />
            </div>
          </div>

          <div v-if="error" class="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
            {{ error }}
          </div>

          <button type="submit" :disabled="loading" class="btn-primary w-full justify-center py-3 disabled:opacity-50 disabled:cursor-not-allowed">
            {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
            <ArrowRight class="w-4 h-4" />
          </button>
        </form>

        <!-- 分隔线 -->
        <div class="flex items-center gap-3 my-5">
          <div class="flex-1 h-px bg-border-subtle"></div>
          <span class="text-xs text-text-muted">或</span>
          <div class="flex-1 h-px bg-border-subtle"></div>
        </div>

        <button @click="demoLogin" :disabled="loading" class="btn-ghost w-full justify-center py-3">
          <Zap class="w-4 h-4 text-accent-cyan" />
          一键体验演示账号
        </button>

        <p class="text-xs text-text-muted text-center mt-5">
          演示账号：demo@nexusrag.ai / demo123456
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import ThemeToggle from '@/components/ThemeToggle.vue'
import { Github, Sparkles, BookOpen, Zap, Shield, FileText, Brain, MessageSquare } from 'lucide-vue-next'

const auth = useAuthStore()

const features = [
  {
    icon: Zap,
    title: '混合检索',
    en: 'Hybrid Retrieval',
    desc: '向量检索 + BM25 关键词检索，使用 RRF 算法融合双路结果，召回准确率提升 35%+',
    color: 'cyan',
  },
  {
    icon: Shield,
    title: '引用溯源',
    en: 'Citation Tracking',
    desc: '每个论断都带 [1][2] 引用标记，可溯源至原文档具体页码与位置',
    color: 'violet',
  },
  {
    icon: Brain,
    title: 'Agent 深度研究',
    en: 'Agent Workflow',
    desc: 'Plan-Retrieve-Reflect-Synthesize 多轮反思，自动拆解子问题并补充检索',
    color: 'pink',
  },
  {
    icon: MessageSquare,
    title: '流式对话',
    en: 'Streaming Chat',
    desc: 'Server-Sent Events 实时流式输出，含 Markdown 渲染、代码高亮',
    color: 'cyan',
  },
  {
    icon: FileText,
    title: '多格式支持',
    en: 'Multi-Format',
    desc: 'PDF / Word / Markdown / TXT 即拖即传，智能分块策略保留语义',
    color: 'violet',
  },
  {
    icon: BookOpen,
    title: '工程化实践',
    en: 'Engineering',
    desc: 'TypeScript 全栈、Pinia 状态管理、JWT 鉴权、Zod 校验、模块化架构',
    color: 'pink',
  },
]

const stack = [
  { name: 'Vue 3.4', cat: '前端框架' },
  { name: 'TypeScript', cat: '类型系统' },
  { name: 'Vite 5', cat: '构建工具' },
  { name: 'Tailwind CSS', cat: '样式' },
  { name: 'Pinia', cat: '状态管理' },
  { name: 'Express 4', cat: '后端框架' },
  { name: 'SQLite', cat: '数据库' },
  { name: 'OpenAI SDK', cat: 'LLM 调用' },
  { name: 'markdown-it', cat: '渲染' },
  { name: 'highlight.js', cat: '代码高亮' },
]
</script>

<template>
  <div class="min-h-screen bg-bg-base text-text-primary relative overflow-hidden">
    <!-- 背景效果 -->
    <div class="absolute inset-0 bg-grid-pattern bg-grid-lg opacity-50 pointer-events-none"></div>
    <div class="absolute top-0 left-1/4 w-[600px] h-[600px] bg-radial-glow rounded-full animate-pulse-glow pointer-events-none"></div>
    <div class="absolute top-1/3 right-0 w-[500px] h-[500px] rounded-full pointer-events-none"
         style="background: radial-gradient(circle, rgba(157,78,221,0.12) 0%, transparent 60%);"></div>

    <!-- 顶部导航 -->
    <header class="relative z-10 border-b border-border-subtle/50 backdrop-blur-md">
      <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-gradient-cv flex items-center justify-center">
            <Sparkles class="w-5 h-5 text-white" />
          </div>
          <div>
            <div class="font-display font-bold text-lg">NexusRAG</div>
            <div class="text-xs text-text-muted -mt-1">智能知识库 · RAG Engine</div>
          </div>
        </div>
        <nav class="flex items-center gap-3">
          <RouterLink v-if="!auth.isLoggedIn" to="/login" class="btn-ghost text-sm">
            登录
          </RouterLink>
          <RouterLink v-if="!auth.isLoggedIn" to="/login" class="btn-primary text-sm">
            开始体验
            <Sparkles class="w-4 h-4" />
          </RouterLink>
          <RouterLink v-else to="/dashboard" class="btn-primary text-sm">
            进入工作台
          </RouterLink>
          <ThemeToggle />
          <a href="https://github.com" target="_blank" class="btn-ghost text-sm" aria-label="GitHub">
            <Github class="w-4 h-4" />
          </a>
        </nav>
      </div>
    </header>

    <!-- Hero -->
    <section class="relative z-10 max-w-7xl mx-auto px-6 pt-24 pb-32 text-center">
      <div class="inline-flex items-center gap-2 px-3 py-1 mb-6 rounded-full border border-accent-cyan/30 bg-accent-cyan/5 text-accent-cyan text-sm animate-fade-in">
        <span class="w-2 h-2 rounded-full bg-accent-cyan animate-pulse"></span>
        Vibecoding 出品 · 简历级项目
      </div>

      <h1 class="font-display font-bold text-6xl md:text-7xl leading-tight mb-6 animate-slide-up">
        让 AI 基于你的文档<br />
        <span class="gradient-text">精准回答每一个问题</span>
      </h1>

      <p class="text-xl text-text-secondary max-w-3xl mx-auto mb-10 leading-relaxed animate-slide-up" style="animation-delay: 0.1s">
        NexusRAG 是一个具备 <span class="text-accent-cyan font-medium">混合检索</span> ·
        <span class="text-accent-violet font-medium">引用溯源</span> ·
        <span class="text-accent-pink font-medium">Agent 工作流</span> 的企业级 RAG 系统。
        上传 PDF / Word / Markdown，让 AI 真正理解你的知识。
      </p>

      <div class="flex flex-wrap items-center justify-center gap-4 animate-slide-up" style="animation-delay: 0.2s">
        <RouterLink :to="auth.isLoggedIn ? '/dashboard' : '/login'" class="btn-primary text-base px-7 py-3">
          <Sparkles class="w-5 h-5" />
          {{ auth.isLoggedIn ? '进入工作台' : '一键体验演示' }}
        </RouterLink>
        <a href="#features" class="btn-ghost text-base px-7 py-3">
          了解更多
        </a>
      </div>

      <!-- 数据指标 -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto mt-20 animate-fade-in" style="animation-delay: 0.4s">
        <div class="glass-card p-5">
          <div class="font-display font-bold text-3xl text-accent-cyan">3+</div>
          <div class="text-sm text-text-secondary mt-1">检索算法</div>
        </div>
        <div class="glass-card p-5">
          <div class="font-display font-bold text-3xl text-accent-violet">4</div>
          <div class="text-sm text-text-secondary mt-1">文档格式</div>
        </div>
        <div class="glass-card p-5">
          <div class="font-display font-bold text-3xl text-accent-pink">2</div>
          <div class="text-sm text-text-secondary mt-1">问答模式</div>
        </div>
        <div class="glass-card p-5">
          <div class="font-display font-bold text-3xl text-accent-cyan">100%</div>
          <div class="text-sm text-text-secondary mt-1">TypeScript</div>
        </div>
      </div>
    </section>

    <!-- 特性卡片 -->
    <section id="features" class="relative z-10 max-w-7xl mx-auto px-6 py-20">
      <div class="text-center mb-16">
        <div class="text-accent-cyan text-sm font-mono mb-3">/ FEATURES</div>
        <h2 class="font-display font-bold text-4xl md:text-5xl mb-4">六大核心能力</h2>
        <p class="text-text-secondary text-lg">每一项都是 RAG 系统的硬核技术点</p>
      </div>

      <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
        <div
          v-for="f in features"
          :key="f.title"
          class="glass-card p-6 hover:border-accent-cyan/40 transition-all duration-300 hover:-translate-y-1 group"
        >
          <div class="flex items-start gap-4">
            <div
              class="w-11 h-11 rounded-lg flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform"
              :class="{
                'bg-accent-cyan/10 text-accent-cyan': f.color === 'cyan',
                'bg-accent-violet/10 text-accent-violet': f.color === 'violet',
                'bg-accent-pink/10 text-accent-pink': f.color === 'pink',
              }"
            >
              <component :is="f.icon" class="w-5 h-5" />
            </div>
            <div class="flex-1">
              <div class="flex items-baseline gap-2 mb-1">
                <h3 class="font-display font-semibold text-lg">{{ f.title }}</h3>
                <span class="text-xs text-text-muted font-mono">{{ f.en }}</span>
              </div>
              <p class="text-sm text-text-secondary leading-relaxed">{{ f.desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 技术栈 -->
    <section class="relative z-10 max-w-7xl mx-auto px-6 py-20">
      <div class="glass-card p-10">
        <div class="text-center mb-10">
          <div class="text-accent-violet text-sm font-mono mb-3">/ TECH STACK</div>
          <h2 class="font-display font-bold text-3xl md:text-4xl mb-3">现代全栈技术栈</h2>
          <p class="text-text-secondary">从数据库到 UI，每一层都精心选型</p>
        </div>

        <div class="flex flex-wrap justify-center gap-3">
          <div
            v-for="t in stack"
            :key="t.name"
            class="px-4 py-2 rounded-lg bg-bg-elevate border border-border-subtle hover:border-accent-cyan/40 transition-colors"
          >
            <div class="font-medium text-text-primary">{{ t.name }}</div>
            <div class="text-xs text-text-muted mt-0.5">{{ t.cat }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="relative z-10 max-w-4xl mx-auto px-6 py-24 text-center">
      <h2 class="font-display font-bold text-4xl md:text-5xl mb-6">
        准备好<span class="gradient-text">让知识说话</span>了吗？
      </h2>
      <p class="text-text-secondary text-lg mb-8">
        无需配置，一键进入演示账号体验完整功能
      </p>
      <RouterLink :to="auth.isLoggedIn ? '/dashboard' : '/login'" class="btn-primary text-base px-8 py-3">
        <Sparkles class="w-5 h-5" />
        立即开始
      </RouterLink>
    </section>

    <!-- Footer -->
    <footer class="relative z-10 border-t border-border-subtle/50 mt-20">
      <div class="max-w-7xl mx-auto px-6 py-8 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-text-muted">
        <div class="flex items-center gap-2">
          <div class="w-6 h-6 rounded bg-gradient-cv flex items-center justify-center">
            <Sparkles class="w-3 h-3 text-white" />
          </div>
          <span>NexusRAG · Built with vibecoding</span>
        </div>
        <div>© 2026 · A Resume-Worthy RAG Project</div>
      </div>
    </footer>
  </div>
</template>

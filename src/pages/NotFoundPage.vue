<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { Home } from 'lucide-vue-next'
import ThemeToggle from '@/components/ThemeToggle.vue'
</script>

<template>
  <div class="min-h-screen bg-bg-base text-text-primary relative overflow-hidden flex items-center justify-center px-4">
    <div class="absolute inset-0 bg-grid-pattern bg-grid-lg opacity-40 pointer-events-none"></div>
    <div class="absolute top-1/4 left-1/3 w-[500px] h-[500px] bg-radial-glow rounded-full animate-pulse-glow pointer-events-none"></div>

    <div class="absolute top-4 right-4 z-20">
      <ThemeToggle />
    </div>

    <div class="relative z-10 text-center max-w-md animate-slide-up">
      <div class="w-20 h-20 rounded-full bg-gradient-cv/20 mx-auto flex items-center justify-center mb-6">
        <span class="text-5xl font-display font-bold gradient-text">404</span>
      </div>
      <h1 class="font-display font-bold text-3xl mb-3">页面未找到</h1>
      <p class="text-text-secondary text-lg mb-8">
        你访问的页面不存在或已被移除，请检查链接是否正确。
      </p>
      <RouterLink to="/" class="btn-primary text-base px-6 py-3 inline-flex items-center gap-2">
        <Home class="w-5 h-5" />
        返回首页
      </RouterLink>
    </div>
  </div>
</template>
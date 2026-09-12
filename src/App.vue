<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { RouterView } from 'vue-router'
import Toast from '@/components/Toast.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useToast } from '@/composables/useToast'

const toast = useToast()
const fatal = ref(false)

// 全局错误边界：组件渲染异常时降级提示，避免白屏
onErrorCaptured((err, _instance, info) => {
  console.error('[App 错误边界]', info, err)
  fatal.value = true
  toast.error('页面出现异常，请刷新重试')
  return false
})
</script>

<template>
  <Toast />
  <ConfirmDialog />

  <div v-if="fatal" class="min-h-screen bg-bg-base text-text-primary flex items-center justify-center p-6">
    <div class="glass-card p-10 max-w-md text-center">
      <div class="w-14 h-14 rounded-full bg-red-500/10 mx-auto flex items-center justify-center mb-4">
        <span class="text-2xl">⚠️</span>
      </div>
      <h1 class="font-display font-bold text-xl mb-2">页面出了点问题</h1>
      <p class="text-text-secondary text-sm mb-6">渲染时发生异常。你可以刷新页面重试，或返回首页。</p>
      <div class="flex justify-center gap-3">
        <button class="btn-ghost" @click="fatal = false">重试</button>
        <a href="/" class="btn-primary">返回首页</a>
      </div>
    </div>
  </div>

  <RouterView v-else v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </RouterView>
</template>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

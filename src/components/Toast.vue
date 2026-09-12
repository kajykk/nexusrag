<script setup lang="ts">
import { useToast } from '@/composables/useToast'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-vue-next'

const { toasts, remove } = useToast()

const iconMap = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
} as const

const classMap = {
  success: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400',
  error: 'border-red-500/40 bg-red-500/10 text-red-400',
  info: 'border-accent-cyan/40 bg-accent-cyan/10 text-accent-cyan',
} as const
</script>

<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[100] flex flex-col gap-2 items-end pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl border shadow-xl backdrop-blur-md max-w-sm animate-slide-up"
          :class="classMap[t.type]"
        >
          <component :is="iconMap[t.type]" class="w-4 h-4 shrink-0" />
          <span class="text-sm font-medium">{{ t.message }}</span>
          <button
            class="ml-2 p-0.5 rounded hover:opacity-70 transition-opacity shrink-0"
            :class="t.type === 'error' ? 'text-red-300' : ''"
            aria-label="关闭提示"
            @click="remove(t.id)"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(30px);
}
.toast-move {
  transition: transform 0.2s ease;
}
</style>
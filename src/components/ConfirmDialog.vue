<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useConfirm } from '@/composables/useConfirm'
import { AlertTriangle } from 'lucide-vue-next'

const { state, settle } = useConfirm()

const cancelBtn = ref<HTMLButtonElement | null>(null)

function handleKeydown(e: KeyboardEvent) {
  if (!state.value.open) return
  if (e.key === 'Escape') {
    e.preventDefault()
    settle(false)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    settle(true)
  }
}

watch(
  () => state.value.open,
  (open) => {
    if (open) {
      requestAnimationFrame(() => cancelBtn.value?.focus())
      document.addEventListener('keydown', handleKeydown)
    } else {
      document.removeEventListener('keydown', handleKeydown)
    }
  },
)

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="state.open"
        class="fixed inset-0 z-[90] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
        role="dialog"
        aria-modal="true"
        :aria-label="state.options.title || '确认操作'"
        @click.self="settle(false)"
      >
        <div
          class="glass-card p-6 w-full max-w-sm animate-slide-up"
          @click.stop
        >
          <div class="flex items-start gap-3 mb-4">
            <div
              class="w-10 h-10 rounded-lg shrink-0 flex items-center justify-center"
              :class="state.options.danger ? 'bg-red-500/10 text-red-400' : 'bg-accent-cyan/10 text-accent-cyan'"
            >
              <AlertTriangle class="w-5 h-5" />
            </div>
            <div class="min-w-0">
              <h3 class="font-display font-bold text-lg">{{ state.options.title || '确认操作' }}</h3>
              <p v-if="state.options.message" class="text-sm text-text-secondary mt-1 leading-relaxed">
                {{ state.options.message }}
              </p>
            </div>
          </div>
          <div class="flex gap-3 pt-2">
            <button
              ref="cancelBtn"
              class="btn-ghost flex-1 justify-center"
              @click="settle(false)"
            >
              {{ state.options.cancelText || '取消' }}
            </button>
            <button
              class="btn-primary flex-1 justify-center"
              :class="state.options.danger ? '!bg-red-500 !bg-none hover:shadow-red-500/30' : ''"
              @click="settle(true)"
            >
              {{ state.options.confirmText || '确认' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

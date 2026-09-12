<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { Quote, X } from 'lucide-vue-next'
import type { Citation } from '@/api/types'

const props = defineProps<{
  citations: Citation[]
  highlightId?: number | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const panel = ref<HTMLElement | null>(null)
const closeBtn = ref<HTMLButtonElement | null>(null)

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.preventDefault()
    emit('close')
    return
  }
  // 简易焦点陷阱：Tab 在面板内循环
  if (e.key !== 'Tab' || !panel.value) return
  const focusables = panel.value.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
  )
  if (focusables.length === 0) return
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

onMounted(() => {
  closeBtn.value?.focus()
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

// 高亮 id 变化时（点击新引用）确保在视口内
watch(
  () => props.highlightId,
  (id) => {
    if (id == null) return
    nextTickFocus(id)
  },
)

function nextTickFocus(id: number) {
  requestAnimationFrame(() => {
    const el = panel.value?.querySelector<HTMLElement>(`[data-cid="${id}"]`)
    el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  })
}
</script>

<template>
  <aside
    ref="panel"
    role="dialog"
    aria-modal="true"
    aria-label="引用来源"
    class="absolute right-0 top-0 bottom-0 w-96 max-w-[90vw] bg-bg-card border-l border-border-subtle z-30 overflow-y-auto shadow-2xl"
  >
    <div class="sticky top-0 bg-bg-card/95 backdrop-blur border-b border-border-subtle px-5 py-3 flex items-center justify-between">
      <div class="flex items-center gap-2">
        <Quote class="w-4 h-4 text-accent-cyan" />
        <h3 class="font-display font-semibold">引用来源</h3>
        <span class="badge badge-cyan">{{ citations.length }}</span>
      </div>
      <button
        ref="closeBtn"
        class="p-1.5 rounded hover:bg-bg-hover transition-colors"
        aria-label="关闭引用面板"
        @click="emit('close')"
      >
        <X class="w-4 h-4" />
      </button>
    </div>
    <div class="p-5 space-y-4">
      <div
        v-for="c in citations"
        :key="c.id"
        :data-cid="c.id"
        class="glass-card p-4 transition-colors"
        :class="c.id === highlightId ? 'border-accent-cyan/60 ring-1 ring-accent-cyan/30' : ''"
      >
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2 min-w-0">
            <div class="w-7 h-7 rounded-md bg-accent-cyan/10 text-accent-cyan font-mono font-bold text-sm flex items-center justify-center shrink-0">
              {{ c.id }}
            </div>
            <div class="text-sm font-medium truncate">{{ c.docName }}</div>
          </div>
          <div v-if="c.page" class="text-xs text-text-muted shrink-0 ml-2">P. {{ c.page }}</div>
        </div>
        <div class="text-sm text-text-secondary leading-relaxed border-l-2 border-accent-cyan/30 pl-3 italic">
          {{ c.content }}
        </div>
        <div class="text-xs text-text-muted mt-2">相关度：{{ (c.score * 100).toFixed(1) }}%</div>
      </div>
    </div>
  </aside>
</template>

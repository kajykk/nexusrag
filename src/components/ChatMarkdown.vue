<script setup lang="ts">
import { useMarkdown } from '@/composables/useMarkdown'
import type { Citation } from '@/api/types'

const props = defineProps<{
  content: string
  citations?: Citation[]
}>()

const emit = defineEmits<{
  (e: 'citation-click', citation: Citation): void
}>()

// 每条消息一个组件实例，useMarkdown 内部的 computed 随实例缓存：
// 流式更新时仅当前消息重新渲染，其余消息命中缓存不重复解析
const { rendered } = useMarkdown(
  () => props.content,
  () => props.citations || [],
)

// 事件委托：点击引用标记时按 data-citation-id 回查引用对象并抛给父组件
function onRootClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  const el = target.closest('.citation-ref') as HTMLElement | null
  if (!el || !props.citations?.length) return
  const id = Number(el.dataset.citationId)
  if (!Number.isFinite(id)) return
  const citation = props.citations.find((c) => c.id === id)
  if (citation) emit('citation-click', citation)
}
</script>

<template>
  <div class="markdown-body" @click="onRootClick" v-html="rendered" />
</template>

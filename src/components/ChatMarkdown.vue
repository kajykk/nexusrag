<script setup lang="ts">
import { useMarkdown } from '@/composables/useMarkdown'
import type { Citation } from '@/api/types'

const props = defineProps<{
  content: string
  citations?: Citation[]
}>()

// 每条消息一个组件实例，useMarkdown 内部的 computed 随实例缓存：
// 流式更新时仅当前消息重新渲染，其余消息命中缓存不重复解析
const { rendered } = useMarkdown(
  () => props.content,
  () => props.citations || [],
)
</script>

<template>
  <div class="markdown-body" v-html="rendered" />
</template>

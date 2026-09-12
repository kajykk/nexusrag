<script setup lang="ts">
import { useTheme } from '@/composables/useTheme'
import { Sun, Moon } from 'lucide-vue-next'

const { isDark, toggleTheme } = useTheme()
</script>

<template>
  <button
    type="button"
    class="btn-ghost !px-2.5"
    :aria-label="isDark ? '切换到亮色主题' : '切换到暗色主题'"
    :title="isDark ? '切换到亮色主题' : '切换到暗色主题'"
    @click="toggleTheme"
  >
    <Moon v-if="isDark" class="w-4 h-4" />
    <Sun v-else class="w-4 h-4" />
  </button>
</template>

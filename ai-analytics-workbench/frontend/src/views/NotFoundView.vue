<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <div class="page not-found">
    <h2>404</h2>
    <p class="subtitle">页面不存在或已被移除</p>
    <RouterLink
      to="/"
      class="btn-primary link-home"
    >
      返回首页
    </RouterLink>
  </div>
</template>

<style scoped>
.not-found {
  text-align: center;
  padding: 80px 24px;
}
.not-found h2 {
  font-size: 64px;
  margin: 0 0 8px;
  color: var(--primary);
}
.subtitle {
  color: #64748b;
  margin: 0 0 24px;
}
.link-home {
  display: inline-block;
}
</style>

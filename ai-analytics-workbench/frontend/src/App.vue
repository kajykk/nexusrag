<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const menus = [
  { key: 'datasets', label: '数据集管理', icon: '📊' },
  { key: 'analysis', label: '数据分析', icon: '🤖' },
  { key: 'reports', label: '分析报告', icon: '📄' },
]

const activeKey = computed(() => route.name as string)

function navigate(key: string) {
  router.push({ name: key })
}
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="logo">
        <span class="logo-icon">🧠</span>
        <div class="logo-text">
          <h1>AI 数据分析工作台</h1>
          <p>自然语言驱动的数据分析平台</p>
        </div>
      </div>
      <nav class="menu">
        <button
          v-for="m in menus"
          :key="m.key"
          class="menu-item"
          :class="{ active: activeKey === m.key }"
          @click="navigate(m.key)"
        >
          <span class="menu-icon">{{ m.icon }}</span>
          <span>{{ m.label }}</span>
        </button>
      </nav>
      <div class="sidebar-footer">
        <p>Vue3 · FastAPI · PostgreSQL</p>
        <p>Redis · WebSocket · Docker</p>
      </div>
    </aside>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 260px;
  background: var(--sidebar);
  color: #cbd5e1;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  height: 100vh;
}

.logo {
  padding: 24px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo-icon {
  font-size: 32px;
}

.logo-text h1 {
  font-size: 16px;
  margin: 0;
  color: #fff;
  font-weight: 600;
}

.logo-text p {
  font-size: 12px;
  margin: 4px 0 0;
  color: #64748b;
}

.menu {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 8px;
  font-size: 14px;
  text-align: left;
  transition: all 0.2s;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #e2e8f0;
}

.menu-item.active {
  background: var(--primary);
  color: #fff;
}

.menu-icon {
  font-size: 18px;
}

.sidebar-footer {
  padding: 16px 20px;
  font-size: 11px;
  color: #475569;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar-footer p {
  margin: 2px 0;
}

.content {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
  max-width: 100%;
}
</style>

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 路由级代码分割：各页面独立 chunk，首屏只加载当前路由
const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/pages/HomePage.vue'),
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/pages/LoginPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/pages/DashboardPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/kb/:id',
    name: 'kb-detail',
    component: () => import('@/pages/KbDetailPage.vue'),
    meta: { requiresAuth: true },
    props: true,
  },
  {
    path: '/chat/:kbId/:sessionId?',
    name: 'chat',
    component: () => import('@/pages/ChatPage.vue'),
    meta: { requiresAuth: true },
    props: true,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局前置守卫
router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  // 首次加载时从 localStorage 恢复 token
  if (!auth.token) auth.restore()

  if (to.meta.requiresAuth && !auth.token) {
    next({ name: 'login', query: { redirect: to.fullPath } })
  } else if (to.meta.guestOnly && auth.token) {
    next({ name: 'dashboard' })
  } else {
    next()
  }
})

export default router

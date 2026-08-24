import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/pages/HomePage.vue'
import LoginPage from '@/pages/LoginPage.vue'
import DashboardPage from '@/pages/DashboardPage.vue'
import KbDetailPage from '@/pages/KbDetailPage.vue'
import ChatPage from '@/pages/ChatPage.vue'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomePage,
  },
  {
    path: '/login',
    name: 'login',
    component: LoginPage,
    meta: { guestOnly: true },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: DashboardPage,
    meta: { requiresAuth: true },
  },
  {
    path: '/kb/:id',
    name: 'kb-detail',
    component: KbDetailPage,
    meta: { requiresAuth: true },
    props: true,
  },
  {
    path: '/chat/:kbId/:sessionId?',
    name: 'chat',
    component: ChatPage,
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

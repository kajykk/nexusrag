import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/datasets',
  },
  {
    path: '/datasets',
    name: 'datasets',
    component: () => import('@/views/DatasetsView.vue'),
    meta: { title: '数据集管理' },
  },
  {
    path: '/analysis',
    name: 'analysis',
    component: () => import('@/views/AnalysisView.vue'),
    meta: { title: '数据分析' },
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('@/views/ReportsView.vue'),
    meta: { title: '分析报告' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 页面标题跟随路由
router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · AI 数据分析工作台` : 'AI 数据分析工作台'
})

export default router

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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { initTheme } from './composables/useTheme'
import { initWebVitals } from './utils/webVitals'

// 性能监控：Core Web Vitals 采集（LCP/INP/CLS/FCP/TTFB）
initWebVitals()

// 主题初始化（暗色默认，持久化，防止 FOUC）
initTheme()

// 创建Vue应用实例
const app = createApp(App)

// 使用路由和状态管理
app.use(createPinia())
app.use(router)

// 挂载应用
app.mount('#app')

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'

// 创建Vue应用实例
const app = createApp(App)

// 使用路由和状态管理
app.use(createPinia())
app.use(router)

// 挂载应用
app.mount('#app')

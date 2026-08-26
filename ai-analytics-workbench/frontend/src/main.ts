import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// 全局兜底：未捕获错误统一记录，避免只有控制台可见
app.config.errorHandler = (err, _instance, info) => {
  console.error('[global-error]', err, `\n触发于: ${info}`)
}

app.mount('#app')

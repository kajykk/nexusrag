import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import { compression } from 'vite-plugin-compression2'
import { fileURLToPath, URL } from 'node:url'

// https://vite.dev/config/
export default defineConfig(async ({ command }) => ({
  plugins: [
    vue(),
    // PWA 支持：离线缓存静态资源
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      manifest: {
        name: 'NexusRAG 智能知识库',
        short_name: 'NexusRAG',
        description: '基于 RAG 的智能知识管理与问答系统',
        theme_color: '#0A0A0F',
        background_color: '#0A0A0F',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        lang: 'zh-CN',
        icons: [
          { src: '/favicon.svg', sizes: 'any', type: 'image/svg+xml' }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//, /^\/ws\//],
        runtimeCaching: [
          {
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif)$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'image-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 60 * 60 * 24 * 7 }
            }
          }
        ],
        skipWaiting: true,
        clientsClaim: true,
        cleanupOutdatedCaches: true
      },
      devOptions: { enabled: false }
    }),
    // Brotli 预压缩（生产环境）：比 gzip 小 15-25%
    command === 'build' &&
      compression({
        algorithms: ['brotliCompress'],
        exclude: [/\.png$/, /\.jpg$/, /\.jpeg$/, /\.gif$/, /\.webp$/, /\.ico$/, /\.woff2$/],
        threshold: 1024
      }),
    // 开发环境启用组件定位器（仅 dev）
    command === 'serve' &&
      (await import('unplugin-vue-dev-locator/vite')).default()
  ].filter(Boolean),
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.log('proxy error', err)
          })
        }
      }
    }
  },
  build: {
    target: 'es2020',
    sourcemap: 'hidden',
    // 暴露 >500KB 的大 chunk
    chunkSizeWarningLimit: 500,
    // 生产环境 drop console/debugger
    esbuild: {
      drop: command === 'build' ? ['console', 'debugger'] : undefined
    },
    rollupOptions: {
      output: {
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames(assetInfo) {
          const info = assetInfo.name || ''
          if (/\.(png|jpe?g|gif|svg)$/.test(info)) return 'assets/images/[name]-[hash][extname]'
          if (info.endsWith('.css')) return 'assets/[name]-[hash][extname]'
          return 'assets/[name]-[hash][extname]'
        },
        // 代码分割
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined
          if (id.includes('vue-router')) return 'router'
          if (id.includes('pinia')) return 'state'
          if (/[\\/]node_modules[\\/](@vue|vue)[\\/]/.test(id)) return 'vue-core'
          if (id.includes('highlight.js')) return 'highlight'
          if (id.includes('markdown-it')) return 'markdown'
          if (id.includes('lucide-vue-next')) return 'icons'
          if (id.includes('axios')) return 'http'
          return 'vendor'
        }
      }
    }
  },
  // 依赖预构建优化
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'pinia',
      'axios',
      'highlight.js',
      'markdown-it'
    ]
  }
}))
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

const backendTarget = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000'
const backendUrl = new URL(backendTarget)
const backendPort = backendUrl.port || (backendUrl.protocol === 'https:' ? '443' : '80')

// Vite 配置：别名 @ 指向 src，便于 `import x from '@/api/...'`
export default defineConfig({
  // 并行运行 MySQL 和独立演示前端时隔离依赖优化缓存，避免一个 Vite
  // 进程重建 ECharts 等依赖后，另一个进程仍请求旧缓存并返回 504。
  cacheDir: `node_modules/.vite-${backendPort}`,
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    open: false,
    proxy: { '/api': { target: backendTarget, changeOrigin: true } },
  },
})

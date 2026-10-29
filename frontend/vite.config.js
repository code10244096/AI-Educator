import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          const p = id.replace(/\\/g, '/')
          if (
            p.includes('/node_modules/react/') ||
            p.includes('/node_modules/react-dom/') ||
            p.includes('/node_modules/react-router-dom/') ||
            p.includes('/node_modules/react-router/') ||
            p.includes('/node_modules/@remix-run/router/') ||
            p.includes('/node_modules/scheduler/')
          ) {
            return 'vendor-react'
          }
        },
      },
    },
  },
  server: {
    host: '127.0.0.1',
    port: 3000,
    strictPort: false,
    open: false,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite proxies /api/* to the FastAPI backend on port 8000,
// so the frontend can use relative /api paths in development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})

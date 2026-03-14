import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  // For GitHub Project Pages this should be `/${repo}/`.
  // Ensure it starts with a single leading slash, otherwise Vite may interpret it as a filesystem path.
  const rawBase = env.VITE_BASE || '/'
  const base = rawBase === '/' ? '/' : `/${rawBase.replace(/^\/+/, '')}`

  return {
    base,
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        },
      },
    },
  }
})

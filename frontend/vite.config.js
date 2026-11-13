import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        configure(proxy) {
          proxy.on('proxyReq', (proxyRequest, request) => {
            const pathname = new URL(request.url, 'http://127.0.0.1').pathname
            if (pathname === '/api/audit' || pathname.startsWith('/api/audit/')) {
              const auditKey = process.env.AUDIT_API_KEY
              if (auditKey) {
                proxyRequest.setHeader('Authorization', `Bearer ${auditKey}`)
              }
            }
          })
        },
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})

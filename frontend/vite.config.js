import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './', // Ensures relative paths in HTML & assets (important for Vercel)
  build: {
    outDir: 'dist', // This must match vercel.json's distDir
  },
  server: {
    proxy: {
      // This rule proxies any request that starts with "/api"
      // to your backend server running on port 8000.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const extraHost = process.env.VITE_ALLOWED_HOST

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: extraHost ? ['localhost', extraHost] : ['localhost'],
  },
})

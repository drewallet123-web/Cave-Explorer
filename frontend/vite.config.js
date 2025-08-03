import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // This makes it accessible from outside container
    port: 3000,
    strictPort: true,
    watch: {
      usePolling: true
    }
  }
})

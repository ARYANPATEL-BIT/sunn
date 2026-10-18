import basicSsl from '@vitejs/plugin-basic-ssl'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Phones only allow the microphone on https pages, so the dev server uses a self-signed
// certificate. An https page can't call the http API directly, so /api is proxied to it.
export default defineConfig({
  plugins: [react(), basicSsl()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', rewrite: (path) => path.replace(/^\/api/, '') },
    },
  },
})

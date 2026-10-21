import fs from 'node:fs'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Phones only allow the microphone on https pages. The certificate comes from mkcert, whose
// local CA this machine trusts, so there's no browser warning (README: https).
const CERT = new URL('./certs/cert.pem', import.meta.url)
const KEY = new URL('./certs/key.pem', import.meta.url)

export default defineConfig(({ command }) => {
  const hasCerts = fs.existsSync(CERT) && fs.existsSync(KEY)
  if (command === 'serve' && !hasCerts) {
    console.warn(
      '\n[notice] web/certs/cert.pem and key.pem not found. Starting HTTP on localhost.\n' +
        'Localhost is treated as a Secure Context by desktop browsers (mic works).\n' +
        'For mobile testing over LAN, create certs with mkcert (see README.md).\n',
    )
  }
  return {
    plugins: [react()],
    server: {
      https: command === 'serve' && hasCerts ? { cert: fs.readFileSync(CERT), key: fs.readFileSync(KEY) } : undefined,
      // `npm run tunnel` serves this through a random *.trycloudflare.com address.
      allowedHosts: ['.trycloudflare.com'],
      // The app calls relative /api/*; the API itself is plain http on this machine. Going
      // through here keeps the browser on one origin, so the session cookie just works.
      proxy: {
        '/api': { target: 'http://localhost:8000', rewrite: (path) => path.replace(/^\/api/, '') },
      },
    },
  }
})

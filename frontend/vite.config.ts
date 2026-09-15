import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Load .env from the repo root so frontend & backend share one env file
  envDir: path.resolve(__dirname, '..'),
  server: {
    headers: {
      // Required for Google OAuth popup to postMessage back to the opener window.
      // The default "same-origin" blocks it; "same-origin-allow-popups" fixes it.
      'Cross-Origin-Opener-Policy': 'same-origin-allow-popups',
    },
  },
})

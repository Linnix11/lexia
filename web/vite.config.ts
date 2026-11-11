/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// En developpement, /api/* est relaye vers l'API FastAPI (uvicorn api.main:app --port 8000).
// En production, definir VITE_API_URL (ex. https://api.lexia.fr) au moment du build.
const API = process.env.LEXIA_API ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // changeOrigin: false : l'API compare l'en-tete Origin a l'hote (protection contre les requetes intersites)
      '/api': { target: API, changeOrigin: false, rewrite: (p) => p.replace(/^\/api/, '') },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/setupTests.ts'],
  },
})

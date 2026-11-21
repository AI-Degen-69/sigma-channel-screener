import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const dataFile = fileURLToPath(new URL('./screener_data.json', import.meta.url))

// monthly_screener.py writes screener_data.json next to the standalone dashboard, but Vite only
// serves public/. Serve that generated snapshot directly in dev and emit the same file in builds,
// so there is a single source of truth and a refresh can never leave a stale copy behind.
function screenerData(): Plugin {
  return {
    name: 'screener-data',
    configureServer(server) {
      server.middlewares.use('/screener_data.json', (_req, res, next) => {
        if (!existsSync(dataFile)) return next()
        res.setHeader('Content-Type', 'application/json')
        res.setHeader('Cache-Control', 'no-store')
        res.end(readFileSync(dataFile))
      })
    },
    generateBundle() {
      if (!existsSync(dataFile)) return
      this.emitFile({ type: 'asset', fileName: 'screener_data.json', source: readFileSync(dataFile) })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), screenerData()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
})

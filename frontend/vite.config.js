import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // orchestrator/server.py - run `python server.py` from orchestrator/
  server: { proxy: { '/api': 'http://127.0.0.1:8787' } },
})

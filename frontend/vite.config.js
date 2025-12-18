import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'build_final', // این خط خیلی مهم است: خروجی حتماً باید dist باشد
  }
})
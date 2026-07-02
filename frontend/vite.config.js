import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/static/',
  server: {
    // این بخش باعث می‌شود درخواست‌ها به بک‌ند جنگو فرستاده شوند
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/media': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
    }
  },
  // تنظیمات بیلد (به صورت پیش‌فرض روی dist تنظیم است، پس نیازی به تغییر نیست)
})
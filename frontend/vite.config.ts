/// <reference types="vitest/config" />
import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        // Las rutas del servidor (API, panel técnico, estáticos, PDF y audios del estudio) nunca
        // deben responderse con la aplicación: se dejan pasar al servidor.
        navigateFallbackDenylist: [/^\/api\//, /^\/admin\//, /^\/static\//],
        runtimeCaching: [
          {
            // Lectura para uso sin conexión: sesión, grupos y reuniones. NO se guardan finanzas,
            // personas, estudios ni la bitácora.
            urlPattern: ({ url, request }) =>
              request.method === 'GET' &&
              /^\/api\/(auth\/me\/|grupos\/(\d+\/|reuniones\/\d+\/)?)$/.test(url.pathname),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'mdf-api',
              networkTimeoutSeconds: 4,
              expiration: { maxEntries: 80, maxAgeSeconds: 7 * 24 * 60 * 60 },
              cacheableResponse: { statuses: [200] },
            },
          },
        ],
      },
      manifest: {
        name: 'MDF360 · Mundo de Fe México',
        short_name: 'MDF360',
        lang: 'es-MX',
        display: 'standalone',
        start_url: '/',
        theme_color: '#884088',
        background_color: '#ffffff',
        icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }],
      },
    }),
  ],
  resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
  server: { proxy: { '/api': process.env.VITE_API_URL ?? 'http://localhost:8000' } },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
})

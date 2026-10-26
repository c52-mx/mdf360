// Service worker de MDF360: caché de la aplicación, lectura sin conexión y notificaciones push.
import { clientsClaim } from 'workbox-core'
import { CacheableResponsePlugin } from 'workbox-cacheable-response'
import { ExpirationPlugin } from 'workbox-expiration'
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'
import { NetworkFirst } from 'workbox-strategies'

self.skipWaiting()
clientsClaim()
cleanupOutdatedCaches()
precacheAndRoute(self.__WB_MANIFEST)

// Las rutas del servidor (API, panel técnico, estáticos, PDF y audios del estudio) nunca deben
// responderse con la aplicación: se dejan pasar al servidor.
registerRoute(
  new NavigationRoute(createHandlerBoundToURL('index.html'), {
    denylist: [/^\/api\//, /^\/admin\//, /^\/static\//],
  }),
)

// Lectura para uso sin conexión: sesión, grupos y reuniones. NO se guardan finanzas, personas,
// estudios ni la bitácora.
registerRoute(
  ({ url, request }) =>
    request.method === 'GET' &&
    /^\/api\/(auth\/me\/|grupos\/(\d+\/|reuniones\/\d+\/)?)$/.test(url.pathname),
  new NetworkFirst({
    cacheName: 'mdf-api',
    networkTimeoutSeconds: 4,
    plugins: [
      new ExpirationPlugin({ maxEntries: 80, maxAgeSeconds: 7 * 24 * 60 * 60 }),
      new CacheableResponsePlugin({ statuses: [200] }),
    ],
  }),
)

// ---------- Notificaciones push (M1-09) ----------
// Vibración: dos pulsos cortos. El sonido lo define el canal de notificaciones del teléfono.
const VIBRACION = [200, 100, 200]

self.addEventListener('push', (event) => {
  let datos = {}
  try {
    datos = event.data ? event.data.json() : {}
  } catch {
    datos = { cuerpo: event.data ? event.data.text() : '' }
  }
  const opciones = {
    body: datos.cuerpo || '',
    icon: '/icon-192.png',
    badge: '/badge-96.png',
    vibrate: VIBRACION,
    lang: 'es-MX',
    data: { url: datos.url || '/' },
  }
  if (datos.etiqueta) {
    // Un aviso nuevo del mismo tablero reemplaza al anterior, pero vuelve a sonar y vibrar.
    opciones.tag = datos.etiqueta
    opciones.renotify = true
  }
  event.waitUntil(self.registration.showNotification(datos.titulo || 'MDF360', opciones))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const destino = new URL(event.notification.data?.url || '/', self.location.origin).href
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(async (ventanas) => {
      for (const ventana of ventanas) {
        if (new URL(ventana.url).origin === self.location.origin) {
          await ventana.focus()
          if ('navigate' in ventana) await ventana.navigate(destino)
          return
        }
      }
      await self.clients.openWindow(destino)
    }),
  )
})

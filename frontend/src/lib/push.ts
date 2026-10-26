import { api } from './api'

/** ¿Este navegador puede recibir notificaciones push? (iPhone solo con la app instalada). */
export function soportaPush(): boolean {
  return (
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  )
}

/** En iPhone y iPad las notificaciones solo funcionan si la aplicación se agregó a la pantalla de inicio. */
export function requiereInstalar(): boolean {
  if (typeof navigator === 'undefined') return false
  const esApple =
    /iPhone|iPad|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  const instalada =
    window.matchMedia?.('(display-mode: standalone)').matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  return esApple && !instalada
}

export function claveABytes(base64Url: string): Uint8Array<ArrayBuffer> {
  const relleno = '='.repeat((4 - (base64Url.length % 4)) % 4)
  const binario = atob((base64Url + relleno).replace(/-/g, '+').replace(/_/g, '/'))
  const bytes = new Uint8Array(new ArrayBuffer(binario.length))
  for (let i = 0; i < binario.length; i++) bytes[i] = binario.charCodeAt(i)
  return bytes
}

export async function suscripcionActual(): Promise<PushSubscription | null> {
  if (!soportaPush()) return null
  const registro = await navigator.serviceWorker.ready
  return registro.pushManager.getSubscription()
}

/** Pide permiso, crea la suscripción del dispositivo y la registra en el servidor. */
export async function activarPush(clavePublica: string): Promise<'activo' | 'bloqueado'> {
  const permiso = await Notification.requestPermission()
  if (permiso !== 'granted') return 'bloqueado'
  const registro = await navigator.serviceWorker.ready
  const suscripcion =
    (await registro.pushManager.getSubscription()) ??
    (await registro.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: claveABytes(clavePublica),
    }))
  await api('/api/notificaciones/suscribir/', { method: 'POST', body: suscripcion.toJSON() })
  return 'activo'
}

/** Quita el dispositivo del servidor y del navegador. */
export async function desactivarPush(): Promise<void> {
  const suscripcion = await suscripcionActual()
  if (!suscripcion) return
  await api('/api/notificaciones/desuscribir/', {
    method: 'POST',
    body: { endpoint: suscripcion.endpoint },
  })
  await suscripcion.unsubscribe()
}

/** Al cerrar sesión: que este teléfono deje de recibir los avisos de la persona que se va. */
export async function quitarDispositivo(): Promise<void> {
  try {
    await desactivarPush()
  } catch {
    // sin conexión o sin suscripción: no debe impedir cerrar sesión
  }
}

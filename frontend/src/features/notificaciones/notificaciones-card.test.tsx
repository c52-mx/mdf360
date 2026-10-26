import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { InvitacionAvisos, NotificacionesCard } from './notificaciones-card'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

let suscripcion: { endpoint: string; toJSON: () => unknown; unsubscribe: () => Promise<boolean> } | null
let permiso: NotificationPermission
let llamadas: string[]

function simularNavegador() {
  const pushManager = {
    getSubscription: vi.fn(() => Promise.resolve(suscripcion)),
    subscribe: vi.fn(() => {
      suscripcion = {
        endpoint: 'https://push.example/1',
        toJSON: () => ({ endpoint: 'https://push.example/1', keys: { p256dh: 'p', auth: 'a' } }),
        unsubscribe: () => {
          suscripcion = null
          return Promise.resolve(true)
        },
      }
      return Promise.resolve(suscripcion)
    }),
  }
  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true,
    value: { ready: Promise.resolve({ pushManager }) },
  })
  vi.stubGlobal('PushManager', class {})
  vi.stubGlobal(
    'Notification',
    Object.assign(
      vi.fn(),
      {
        requestPermission: vi.fn(() => Promise.resolve(permiso)),
      },
      {
        get permission() {
          return permiso
        },
      },
    ),
  )
}

function simularServidor(disponible = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (url.includes('/config/'))
        return json(200, { disponible, clave_publica: disponible ? 'AQID' : '' })
      llamadas.push(`${init?.method ?? 'GET'} ${url}`)
      return init?.method === 'POST' && url.includes('/desuscribir/')
        ? Promise.resolve(new Response(null, { status: 204 }))
        : json(200, {})
    }),
  )
}

const montar = (ui: React.ReactElement) =>
  render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>)

beforeEach(() => {
  suscripcion = null
  permiso = 'default'
  llamadas = []
})

afterEach(() => {
  vi.unstubAllGlobals()
  Reflect.deleteProperty(navigator, 'serviceWorker')
})

describe('NotificacionesCard', () => {
  it('sin soporte del navegador lo explica y no ofrece activar', async () => {
    simularServidor()
    montar(<NotificacionesCard />)
    expect(await screen.findByText(/no puede recibir avisos/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Activar avisos' })).toBeNull()
  })

  it('activa: pide permiso, se suscribe y registra el dispositivo', async () => {
    simularNavegador()
    simularServidor()
    permiso = 'granted'
    montar(<NotificacionesCard />)
    fireEvent.click(await screen.findByRole('button', { name: 'Activar avisos' }))
    expect(await screen.findByRole('button', { name: 'Desactivar' })).toBeInTheDocument()
    expect(llamadas).toContain('POST /api/notificaciones/suscribir/')
  })

  it('si la persona no concede el permiso, explica cómo permitirlo', async () => {
    simularNavegador()
    simularServidor()
    permiso = 'default'
    const original = Notification.requestPermission as ReturnType<typeof vi.fn>
    original.mockImplementation(() => {
      permiso = 'denied'
      return Promise.resolve('denied')
    })
    montar(<NotificacionesCard />)
    fireEvent.click(await screen.findByRole('button', { name: 'Activar avisos' }))
    expect(await screen.findByText(/Bloqueaste los avisos/)).toBeInTheDocument()
    expect(llamadas).not.toContain('POST /api/notificaciones/suscribir/')
  })

  it('con el dispositivo activo permite mandar una prueba y desactivar', async () => {
    simularNavegador()
    simularServidor()
    permiso = 'granted'
    suscripcion = {
      endpoint: 'https://push.example/1',
      toJSON: () => ({}),
      unsubscribe: () => {
        suscripcion = null
        return Promise.resolve(true)
      },
    }
    montar(<NotificacionesCard />)
    fireEvent.click(await screen.findByRole('button', { name: 'Enviarme una prueba' }))
    await waitFor(() => expect(llamadas).toContain('POST /api/notificaciones/probar/'))
    fireEvent.click(screen.getByRole('button', { name: 'Desactivar' }))
    expect(await screen.findByRole('button', { name: 'Activar avisos' })).toBeInTheDocument()
    expect(llamadas).toContain('POST /api/notificaciones/desuscribir/')
  })

  it('si el servidor los tiene apagados lo dice', async () => {
    simularNavegador()
    simularServidor(false)
    montar(<NotificacionesCard />)
    expect(await screen.findByText(/no están activos/)).toBeInTheDocument()
  })
})

describe('InvitacionAvisos', () => {
  it('aparece mientras no se hayan activado y se oculta al activar', async () => {
    simularNavegador()
    simularServidor()
    permiso = 'granted'
    montar(<InvitacionAvisos />)
    fireEvent.click(await screen.findByRole('button', { name: 'Activar avisos' }))
    await waitFor(() => expect(screen.queryByText('No te pierdas los avisos')).toBeNull())
  })

  it('no estorba cuando ya están activos', async () => {
    simularNavegador()
    simularServidor()
    permiso = 'granted'
    suscripcion = { endpoint: 'x', toJSON: () => ({}), unsubscribe: () => Promise.resolve(true) }
    montar(<InvitacionAvisos />)
    await waitFor(() => expect(screen.queryByText('No te pierdas los avisos')).toBeNull())
    expect(screen.queryByRole('button', { name: 'Activar avisos' })).toBeNull()
  })
})

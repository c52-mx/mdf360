import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '@/design-system'
import { QrEnlacesCard } from './qr-enlaces-card'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const enlaces = [
  { tipo: 'grupo', id: 3, nombre: 'Conexión Norte', enlace: '/unirse/abc', requiere_aprobacion: true },
  { tipo: 'ministerio', id: 5, nombre: 'Cafetería', enlace: '/servir/xyz', requiere_aprobacion: false },
  { tipo: 'ministerio', id: 6, nombre: 'Danza', enlace: null, requiere_aprobacion: false },
]

function montar(lista: unknown[] = enlaces, llamadas: { url: string; metodo?: string }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method && init.method !== 'GET') {
        llamadas.push({ url, metodo: init.method })
        return json(201, { enlace: '/servir/nuevo' })
      }
      return json(200, lista)
    }),
  )
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>
        <QrEnlacesCard />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

const elegir = async (nombre: RegExp) => {
  fireEvent.focus(await screen.findByRole('combobox', { name: 'Grupo o ministerio' }))
  fireEvent.click(await screen.findByRole('option', { name: nombre }))
}

afterEach(() => vi.unstubAllGlobals())

describe('QrEnlacesCard', () => {
  it('muestra el QR del grupo elegido y avisa que pasa por aprobación', async () => {
    montar()
    await elegir(/Conexión Norte/)
    expect(await screen.findByRole('img', { name: 'Código QR de Conexión Norte' })).toBeInTheDocument()
    expect(screen.getByText('Con aprobación del líder')).toBeInTheDocument()
    expect(screen.getByText(/\/unirse\/abc/)).toBeInTheDocument()
  })

  it('el QR de un ministerio entra sin aprobación', async () => {
    montar()
    await elegir(/Cafetería/)
    expect(await screen.findByText('Entra sin aprobación')).toBeInTheDocument()
    expect(screen.getByText(/\/servir\/xyz/)).toBeInTheDocument()
  })

  it('un enlace desactivado se puede volver a crear en la ruta del ministerio', async () => {
    const llamadas: { url: string; metodo?: string }[] = []
    montar(enlaces, llamadas)
    await elegir(/Danza/)
    fireEvent.click(await screen.findByRole('button', { name: 'Crear enlace y QR' }))
    await waitFor(() => expect(llamadas).toEqual([{ url: '/api/unidades/6/enlace/', metodo: 'POST' }]))
  })

  it('quien no gestiona a nadie no ve la sección', async () => {
    montar([])
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalled())
    await new Promise((r) => setTimeout(r, 50))
    expect(screen.queryByText('Invitar con un QR')).not.toBeInTheDocument()
  })
})

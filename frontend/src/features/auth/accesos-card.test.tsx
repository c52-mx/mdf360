import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '@/design-system'
import { AccesosCard } from './accesos-card'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const gente = [
  { id: 7, nombre: 'Ana Asistente', whatsapp: '+525500000006', bloqueado: true, activada: true },
  { id: 8, nombre: 'Beto Bueno', whatsapp: '+525500000009', bloqueado: false, activada: true },
]

function montar(llamadas: string[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method === 'POST') {
        llamadas.push(url)
        if (url.endsWith('/unlock/')) return Promise.resolve(new Response(null, { status: 204 }))
        return json(200, {
          user: { nombre: 'Beto Bueno' },
          activation_url: 'https://qa.example/activar/abc',
          whatsapp_url: 'https://wa.me/525500000009?text=hola',
          expires_at: '2026-11-01T12:00:00Z',
        })
      }
      llamadas.push(url)
      return json(200, gente)
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>
        <AccesosCard />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

const elegir = async (nombre: RegExp) => {
  fireEvent.focus(screen.getByRole('combobox', { name: 'Buscar persona' }))
  fireEvent.click(await screen.findByRole('option', { name: nombre }))
}

afterEach(() => vi.unstubAllGlobals())

describe('AccesosCard', () => {
  it('se busca a la persona con un combo y se pide al servidor lo que se escribe', async () => {
    const llamadas: string[] = []
    montar(llamadas)
    fireEvent.change(screen.getByRole('combobox', { name: 'Buscar persona' }), { target: { value: '5500' } })
    await waitFor(() => expect(llamadas.some((u) => u.includes('q=5500'))).toBe(true))
    expect(screen.queryByRole('button', { name: 'Reiniciar acceso' })).not.toBeInTheDocument()
  })

  it('marca a quien está bloqueado y solo a esa persona le ofrece desbloquear', async () => {
    montar([])
    await elegir(/Ana Asistente/)
    expect(screen.getByText('Bloqueado')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Desbloquear' })).toBeInTheDocument()
    await elegir(/Beto Bueno/)
    expect(screen.queryByRole('button', { name: 'Desbloquear' })).not.toBeInTheDocument()
  })

  it('desbloquear llama al servidor y avisa', async () => {
    const llamadas: string[] = []
    montar(llamadas)
    await elegir(/Ana Asistente/)
    fireEvent.click(screen.getByRole('button', { name: 'Desbloquear' }))
    await waitFor(() => expect(llamadas).toContain('/api/auth/users/7/unlock/'))
    expect(await screen.findByText('Ana Asistente ya puede intentar entrar de nuevo.')).toBeInTheDocument()
  })

  it('reiniciar acceso muestra el enlace para mandarlo por WhatsApp', async () => {
    const llamadas: string[] = []
    montar(llamadas)
    await elegir(/Beto Bueno/)
    fireEvent.click(screen.getByRole('button', { name: 'Reiniciar acceso' }))
    expect(await screen.findByRole('link', { name: 'Enviar por WhatsApp' })).toHaveAttribute(
      'href',
      'https://wa.me/525500000009?text=hola',
    )
    expect(llamadas).toContain('/api/auth/users/8/reset/')
  })
})

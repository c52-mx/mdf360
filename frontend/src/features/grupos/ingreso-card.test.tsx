import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '@/design-system'
import { IngresoCard } from './ingreso-card'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const pendiente = {
  id: 7,
  nombre: 'Vecina Nueva',
  whatsapp: '+525570000001',
  estado: 'pendiente',
  whatsapp_url: 'https://wa.me/525570000001?text=hola',
}

function montar(enlace: string | null, llamadas: string[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method === 'POST' || init?.method === 'DELETE') {
        llamadas.push(`${init.method} ${url}`)
        return json(200, { ...pendiente, estado: 'aprobada' })
      }
      return json(200, [pendiente])
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>
        <IngresoCard grupoId={4} enlace={enlace} suspendido={false} />
      </ToastProvider>
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => vi.unstubAllGlobals())

describe('IngresoCard', () => {
  it('sin enlace ofrece crearlo', async () => {
    const llamadas = montar(null)
    fireEvent.click(await screen.findByRole('button', { name: 'Crear enlace y QR' }))
    await waitFor(() => expect(llamadas).toContain('POST /api/grupos/4/enlace/'))
  })

  it('con enlace muestra el QR, el enlace completo y pide confirmar antes de regenerar', async () => {
    const llamadas = montar('/unirse/abc')
    expect(await screen.findByRole('img', { name: 'Código QR del grupo' })).toBeInTheDocument()
    expect(screen.getByText(`${window.location.origin}/unirse/abc`)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Generar uno nuevo' }))
    expect(llamadas).toEqual([])
    fireEvent.click(screen.getByRole('button', { name: 'Sí, generar' }))
    await waitFor(() => expect(llamadas).toContain('POST /api/grupos/4/enlace/'))
  })

  it('lista a quien espera y al aprobarlo ofrece avisarle por WhatsApp', async () => {
    const llamadas = montar('/unirse/abc')
    expect(await screen.findByText('Vecina Nueva')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Aprobar' }))
    await waitFor(() => expect(llamadas).toContain('POST /api/grupos/solicitudes/7/aprobar/'))
    expect(await screen.findByRole('link', { name: 'Avisarle por WhatsApp' })).toHaveAttribute(
      'href',
      'https://wa.me/525570000001?text=hola',
    )
  })

  it('puede rechazar una solicitud', async () => {
    const llamadas = montar('/unirse/abc')
    fireEvent.click(await screen.findByRole('button', { name: 'Rechazar' }))
    await waitFor(() => expect(llamadas).toContain('POST /api/grupos/solicitudes/7/rechazar/'))
  })
})

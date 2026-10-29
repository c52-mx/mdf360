import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AvisoPendiente } from './aviso-pendiente'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

function montar(pendiente: boolean, llamadas: string[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method === 'POST') {
        llamadas.push(url)
        return json(200, { aviso_pendiente: false })
      }
      if (url.includes('/aviso-privacidad/')) return json(200, { version: '1.0', texto: 'Texto oficial' })
      return json(200, { aviso_pendiente: pendiente })
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AvisoPendiente />
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => vi.unstubAllGlobals())

describe('AvisoPendiente', () => {
  it('pide aceptar el aviso nuevo y lo registra', async () => {
    const llamadas = montar(true)
    expect(await screen.findByText(/Actualizamos el aviso de privacidad/)).toBeInTheDocument()
    expect(screen.getByText(/versión 1.0/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Acepto el aviso de privacidad' }))
    await waitFor(() => expect(llamadas).toContain('/api/personas/mi-perfil/aceptar-aviso/'))
  })

  it('no aparece si la persona ya aceptó la versión vigente', async () => {
    montar(false)
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    expect(screen.queryByText(/Actualizamos el aviso/)).toBeNull()
  })
})

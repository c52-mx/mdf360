import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { NuevaPersonaPage } from './nueva-persona-page'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

function setup(post: () => Promise<Response>) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/aviso-privacidad/')) return json(200, { version: '0.1', texto: 'Aviso de ejemplo' })
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method === 'POST') return post()
      return json(404, {})
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <NuevaPersonaPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('NuevaPersonaPage', () => {
  it('no deja guardar hasta aceptar el aviso de privacidad', async () => {
    setup(() => json(201, {}))
    const guardar = await screen.findByRole('button', { name: 'Guardar contacto' })
    expect(guardar).toBeDisabled()
    fireEvent.click(screen.getByLabelText('La persona acepta el aviso de privacidad'))
    expect(guardar).toBeEnabled()
  })

  it('avisa cuando el número ya existe y ofrece abrir el registro', async () => {
    setup(() =>
      json(409, { code: 'duplicate', detail: 'Ya existe una persona con ese número.', persona_id: 7 }),
    )
    fireEvent.change(await screen.findByLabelText('Nombre'), { target: { value: 'María' } })
    fireEvent.change(screen.getByLabelText('Número de WhatsApp'), { target: { value: '5544443333' } })
    fireEvent.click(screen.getByLabelText('La persona acepta el aviso de privacidad'))
    fireEvent.click(screen.getByRole('button', { name: 'Guardar contacto' }))
    const enlace = await screen.findByRole('link', { name: 'Abrir su registro' })
    await waitFor(() => expect(enlace).toHaveAttribute('href', '/personas/7'))
  })
})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MuroFeed } from './muro-feed'
import type { Publicacion } from './types'

const publicacion: Publicacion = {
  id: 7,
  autor: 'Pastor',
  texto: 'Cena navideña para servidores',
  creada_en: '2026-11-09T20:00:00Z',
  audiencias: [{ tipo: 'segmento', id: 1, etiqueta: 'Servidores' }],
  es_mia: false,
  reacciones: { amen: 2 },
  mi_reaccion: null,
  comentarios_total: 1,
}

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

function montar() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MuroFeed />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('MuroFeed', () => {
  it('muestra las publicaciones con su audiencia y cuántas reacciones tienen', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === '/api/muro/') return json(200, { resultados: [publicacion], siguiente: null })
        return json(404, {})
      }),
    )
    montar()
    expect(await screen.findByText('Cena navideña para servidores')).toBeTruthy()
    expect(screen.getByText('Servidores')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Amén, 2' })).toBeTruthy()
    expect(screen.getByText('1 comentarios')).toBeTruthy()
  })

  it('invita a esperar cuando todavía no hay nada', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json(200, { resultados: [], siguiente: null })),
    )
    montar()
    expect(await screen.findByText(/Aún no hay publicaciones para ti/)).toBeTruthy()
  })

  it('reacciona y refleja el cambio sin recargar el muro', async () => {
    const put = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url === '/api/muro/') return json(200, { resultados: [publicacion], siguiente: null })
        if (url === '/api/muro/7/reaccion/' && init?.method === 'PUT') {
          put(init.body)
          return json(200, { ...publicacion, reacciones: { amen: 3 }, mi_reaccion: 'amen' })
        }
        return json(404, {})
      }),
    )
    montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Amén, 2' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Amén, 3' })).toBeTruthy())
    expect(put).toHaveBeenCalledWith(JSON.stringify({ tipo: 'amen' }))
    expect(screen.getByRole('button', { name: 'Amén, 3' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('abre los comentarios y publica uno', async () => {
    const post = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url === '/api/muro/') return json(200, { resultados: [publicacion], siguiente: null })
        if (url === '/api/muro/7/comentarios/' && init?.method === 'POST') {
          post(init.body)
          return json(201, {})
        }
        if (url === '/api/muro/7/comentarios/')
          return json(200, [
            { id: 1, autor: 'Ana', texto: 'Ahí estaré', creado_en: '2026-11-09T21:00:00Z', es_mio: false, puede_quitar: false },
          ])
        return json(404, {})
      }),
    )
    montar()
    fireEvent.click(await screen.findByRole('button', { name: '1 comentarios' }))
    expect(await screen.findByText('Ahí estaré')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Escribe un comentario'), { target: { value: 'Yo también' } })
    fireEvent.click(screen.getByRole('button', { name: 'Comentar' }))
    await waitFor(() => expect(post).toHaveBeenCalledWith(JSON.stringify({ texto: 'Yo también' })))
  })
})

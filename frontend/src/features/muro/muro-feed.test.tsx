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
  fijada: false,
  editada: false,
  puede_editar: false,
  puede_quitar: false,
  puede_moderar: false,
  reportes: 0,
  yo_reporte: false,
}

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

function montar() {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MuroFeed />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

const destinosVacios = (url: string) => (url === '/api/muro/destinos/' ? json(200, []) : null)

describe('MuroFeed', () => {
  it('muestra las publicaciones con su audiencia y cuántas reacciones tienen', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url === '/api/muro/destinos/') return json(200, [])
        if (url === '/api/muro/')
          return json(200, { fijadas: [], resultados: [publicacion], siguiente: null })
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
      vi.fn(
        (url: string) =>
          destinosVacios(url) ?? json(200, { fijadas: [], resultados: [], siguiente: null }),
      ),
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
        if (url === '/api/muro/destinos/') return json(200, [])
        if (url === '/api/muro/')
          return json(200, { fijadas: [], resultados: [publicacion], siguiente: null })
        if (url === '/api/muro/7/reaccion/' && init?.method === 'PUT') {
          put(init.body)
          return json(200, {
            ...publicacion,
            reacciones: { amen: 3 },
            mi_reaccion: 'amen',
          })
        }
        return json(404, {})
      }),
    )
    montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Amén, 2' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Amén, 3' })).toBeTruthy())
    expect(put).toHaveBeenCalledWith(JSON.stringify({ tipo: 'amen' }))
    expect(screen.getByRole('button', { name: 'Amén, 3' }).getAttribute('aria-pressed')).toBe(
      'true',
    )
  })

  it('abre los comentarios y publica uno', async () => {
    const post = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url === '/api/muro/destinos/') return json(200, [])
        if (url === '/api/muro/')
          return json(200, { fijadas: [], resultados: [publicacion], siguiente: null })
        if (url === '/api/muro/7/comentarios/' && init?.method === 'POST') {
          post(init.body)
          return json(201, {})
        }
        if (url === '/api/muro/7/comentarios/')
          return json(200, [
            {
              id: 1,
              autor: 'Ana',
              texto: 'Ahí estaré',
              creado_en: '2026-11-09T21:00:00Z',
              es_mio: false,
              puede_quitar: false,
            },
          ])
        return json(404, {})
      }),
    )
    montar()
    fireEvent.click(await screen.findByRole('button', { name: '1 comentarios' }))
    expect(await screen.findByText('Ahí estaré')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Escribe un comentario'), {
      target: { value: 'Yo también' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Comentar' }))
    await waitFor(() => expect(post).toHaveBeenCalledWith(JSON.stringify({ texto: 'Yo también' })))
  })

  it('quien puede publicar elige las audiencias y publica', async () => {
    const post = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url === '/api/muro/destinos/')
          return json(200, [
            { tipo: 'iglesia', id: 1, etiqueta: 'Toda la iglesia' },
            { tipo: 'segmento', id: 1, etiqueta: 'Servidores' },
          ])
        if (url === '/api/muro/' && init?.method === 'POST') {
          post(init.body)
          return json(201, publicacion)
        }
        if (url === '/api/muro/') return json(200, { fijadas: [], resultados: [], siguiente: null })
        return json(404, {})
      }),
    )
    montar()
    const boton = await screen.findByRole('button', { name: 'Publicar' })
    fireEvent.change(screen.getByLabelText('¿Qué quieres compartir?'), {
      target: { value: 'Cena navideña' },
    })
    // sin audiencia no se puede publicar
    expect((boton as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Servidores' }))
    fireEvent.click(screen.getByRole('button', { name: 'Toda la iglesia' }))
    fireEvent.click(boton)
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith(
        JSON.stringify({
          texto: 'Cena navideña',
          destinos: [
            { tipo: 'iglesia', id: 1 },
            { tipo: 'segmento', id: 1 },
          ],
        }),
      ),
    )
  })

  it('quien no puede publicar no ve el compositor y puede reportar lo ajeno', async () => {
    const reporte = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url === '/api/muro/destinos/') return json(200, [])
        if (url === '/api/muro/7/reportar/' && init?.method === 'POST') {
          reporte(init.body)
          return json(204, null)
        }
        if (url === '/api/muro/')
          return json(200, { fijadas: [], resultados: [publicacion], siguiente: null })
        return json(404, {})
      }),
    )
    montar()
    await screen.findByText('Cena navideña para servidores')
    expect(screen.queryByText('¿Qué quieres compartir?')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Eliminar' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Reportar' }))
    fireEvent.change(screen.getByLabelText('¿Por qué la reportas? (opcional)'), {
      target: { value: 'Es spam' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Enviar reporte' }))
    await waitFor(() => expect(reporte).toHaveBeenCalledWith(JSON.stringify({ motivo: 'Es spam' })))
  })

  it('quien modera ve fijadas arriba, los reportes y puede fijar', async () => {
    const fijar = vi.fn()
    const mia = {
      ...publicacion,
      id: 8,
      texto: 'Aviso fijo',
      fijada: true,
      puede_moderar: true,
      puede_quitar: true,
      reportes: 2,
    }
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url === '/api/muro/destinos/') return json(200, [])
        if (url === '/api/muro/8/' && init?.method === 'PATCH') {
          fijar(init.body)
          return json(200, mia)
        }
        if (url === '/api/muro/')
          return json(200, { fijadas: [mia], resultados: [publicacion], siguiente: null })
        return json(404, {})
      }),
    )
    montar()
    const textos = (await screen.findAllByText(/Aviso fijo|Cena navideña para servidores/)).map(
      (e) => e.textContent,
    )
    expect(textos).toEqual(['Aviso fijo', 'Cena navideña para servidores'])
    expect(screen.getByText('Fijada')).toBeTruthy()
    expect(screen.getByText('2 personas la reportaron.')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Quitar fijado' }))
    await waitFor(() => expect(fijar).toHaveBeenCalledWith(JSON.stringify({ fijada: false })))
  })
})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TableroPanel, type Mensaje } from './tablero-panel'

const mensaje: Mensaje = {
  id: 1,
  origen: { tipo: 'grupo', id: 3, etiqueta: 'Grupo de Conexión · Conexión Norte' },
  autor: 'Laura Pérez',
  texto: 'Reunión este jueves a las 7:30',
  fijado: true,
  creado_en: '2026-10-22T20:00:00Z',
  es_mio: false,
  puede_moderar: true,
}

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

function montar(puedePublicar: boolean) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <TableroPanel origenTipo="grupo" origenId={3} puedePublicar={puedePublicar} />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('TableroPanel', () => {
  it('muestra los mensajes y marca el tablero como visto', async () => {
    const visto = vi.fn(() => Promise.resolve(new Response(null, { status: 204 })))
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url.includes('/visto/') && init?.method === 'POST') return visto()
        return json(200, [mensaje])
      }),
    )
    montar(false)
    expect(await screen.findByText('Reunión este jueves a las 7:30')).toBeInTheDocument()
    expect(screen.getByText('Fijado')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Publicar' })).toBeNull()
    await waitFor(() => expect(visto).toHaveBeenCalledTimes(1))
  })

  it('publica un mensaje con la opción de fijarlo', async () => {
    const publicar = vi.fn((body: Record<string, unknown>) => json(201, { ...mensaje, recibido: body }))
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url.includes('/visto/')) return Promise.resolve(new Response(null, { status: 204 }))
        if (init?.method === 'POST') return publicar(JSON.parse(String(init.body)) as Record<string, unknown>)
        return json(200, [])
      }),
    )
    montar(true)
    expect(await screen.findByText('Todavía no hay mensajes.')).toBeInTheDocument()
    const boton = screen.getByRole('button', { name: 'Publicar' })
    expect(boton).toBeDisabled() // sin texto no se puede publicar
    fireEvent.change(screen.getByLabelText('Nuevo mensaje'), { target: { value: 'Hola a todos' } })
    fireEvent.click(screen.getByLabelText('Fijar arriba'))
    fireEvent.click(boton)
    await waitFor(() => expect(publicar).toHaveBeenCalledTimes(1))
    expect(publicar.mock.calls[0][0]).toEqual({
      origen_tipo: 'grupo',
      origen_id: 3,
      texto: 'Hola a todos',
      fijado: true,
    })
  })

  it('no aparece si la persona no puede leer ese tablero', async () => {
    vi.stubGlobal('fetch', vi.fn(() => json(404, { detail: 'No encontrado' })))
    montar(true)
    await waitFor(() => expect(document.body.textContent).not.toContain('Tablero de mensajes'))
  })

  it('quien puede moderar ve fijar y borrar', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        url.includes('/visto/') ? Promise.resolve(new Response(null, { status: 204 })) : json(200, [mensaje]),
      ),
    )
    montar(false)
    expect(await screen.findByRole('button', { name: /Quitar fijado/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Borrar/ })).toBeInTheDocument()
  })
})

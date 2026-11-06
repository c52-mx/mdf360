import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PersonasPage } from './personas-page'

const json = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))

const persona = (id: number, nombre: string) => ({
  id, nombre_completo: nombre, whatsapp: `55000000${id}`, nivel: 'contacto', activo: true, roles: [],
  grupos: [], grupo_conexion: '', foto: null,
})

function montar(llamadas: string[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      llamadas.push(url)
      if (url.includes('/csrf/')) return json({ csrfToken: 'x' })
      if (url.includes('/api/personas/')) {
        const segunda = url.includes('page=2')
        return json({
          count: 3,
          next: segunda ? null : '/api/personas/?page=2',
          previous: null,
          results: segunda ? [persona(3, 'Ana')] : [persona(1, 'Zoé'), persona(2, 'Beto')],
        })
      }
      return json([])
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <PersonasPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const nombres = () =>
  within(screen.getByRole('region', { name: 'Personas' }))
    .getAllByRole('link')
    .map((l) => l.getAttribute('href'))

afterEach(() => vi.unstubAllGlobals())

describe('PersonasPage', () => {
  it('junta todas las páginas del servidor en una sola tabla ordenada', async () => {
    const llamadas: string[] = []
    montar(llamadas)
    await screen.findAllByRole('link', { name: /Zoé/ })
    expect(nombres()).toEqual(['/personas/3', '/personas/2', '/personas/1']) // incluye la segunda página
    expect(llamadas.filter((u) => u.includes('/api/personas/?'))).toHaveLength(2)
    expect(screen.queryByRole('button', { name: 'Siguiente' })).toBeNull()
  })

  it('se puede ordenar al revés por persona', async () => {
    montar([])
    await screen.findAllByRole('link', { name: /Zoé/ })
    const boton = screen.getByRole('button', { name: /Persona/ })
    fireEvent.click(boton) // ya está ascendente: pasa a descendente
    await waitFor(() => expect(nombres()).toEqual(['/personas/1', '/personas/2', '/personas/3']))
  })
})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { EnviarAvisoCard } from './enviar-aviso-card'

let permisos = ['avisos.personas']
vi.mock('@/features/auth/use-auth', () => ({ useCan: (p: string) => permisos.includes(p) }))

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const destinos = [
  { tipo: 'iglesia', tipo_display: 'Toda la iglesia', id: 1, etiqueta: 'Toda la iglesia' },
  { tipo: 'grupo', tipo_display: 'Grupo de Conexión', id: 4, etiqueta: 'Grupo de Conexión · Norte' },
  { tipo: 'unidad', tipo_display: 'Unidad', id: 2, etiqueta: 'Unidad · Cafetería' },
]

function montar(lista = destinos, llamadas: { url: string; init?: RequestInit }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method === 'POST') {
        llamadas.push({ url, init })
        return json(201, { enviados: [{ tipo: 'iglesia', id: 1, etiqueta: 'x' }], omitidos: [] })
      }
      if (url.includes('/destinos/')) return json(200, lista)
      return json(200, { results: [{ id: 9, nombre_completo: 'Ana Ajena' }] })
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <EnviarAvisoCard />
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => {
  vi.unstubAllGlobals()
  permisos = ['avisos.personas']
})

describe('EnviarAvisoCard', () => {
  it('no aparece para quien no puede publicar en ningún lugar ni escribir a personas', async () => {
    permisos = []
    montar([])
    await waitFor(() => expect(fetch).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: 'Enviar un aviso' })).toBeNull()
  })

  it('envía un mismo aviso a la iglesia, un grupo, una unidad y una persona', async () => {
    const llamadas = montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Enviar un aviso' }))
    fireEvent.change(screen.getByLabelText('Mensaje'), { target: { value: 'Domingo de ayuno' } })
    for (const nombre of ['Toda la iglesia', 'Grupo de Conexión · Norte', 'Unidad · Cafetería']) {
      fireEvent.click(screen.getByRole('checkbox', { name: nombre }))
    }
    fireEvent.change(screen.getByLabelText('Buscar persona'), { target: { value: 'ana' } })
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Ana Ajena' }))
    fireEvent.click(screen.getByRole('button', { name: 'Enviar a 4' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/tablero/masivo/'))
    expect(JSON.parse(String(llamadas[0].init?.body))).toEqual({
      texto: 'Domingo de ayuno',
      destinos: [
        { tipo: 'iglesia', id: 1 },
        { tipo: 'grupo', id: 4 },
        { tipo: 'unidad', id: 2 },
        { tipo: 'persona', id: 9 },
      ],
    })
    expect(await screen.findByText(/Aviso enviado a 1 lugar/)).toBeInTheDocument()
  })

  it('no deja enviar sin mensaje o sin destinos', async () => {
    montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Enviar un aviso' }))
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Mensaje'), { target: { value: 'Hola' } })
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
  })
})

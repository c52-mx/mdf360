import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AvisosPage } from './avisos-page'

vi.mock('./enviar-aviso-card', () => ({ EnviarAvisoCard: () => null }))
vi.mock('./tablero-panel', () => ({ TableroPanel: ({ titulo }: { titulo?: string }) => <p>Panel de {titulo}</p> }))

const json = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))

const tableros = [
  { tipo: 'grupo', tipo_display: 'Grupo de Conexión', id: 4, etiqueta: 'Grupo · Norte', no_leidos: 2, puede_publicar: true },
  { tipo: 'iglesia', tipo_display: 'Toda la iglesia', id: 1, etiqueta: 'Toda la iglesia', no_leidos: 0, puede_publicar: false },
]
const pendiente = {
  id: 31,
  texto: 'Convivio de la iglesia',
  autor: 'Ana Asistente',
  creado_en: '2026-10-28T10:00:00Z',
  estado: 'pendiente',
  estado_display: 'Por autorizar',
  puede_resolver: true,
}

function montar(porAutorizar: unknown, llamadas: string[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json({ csrfToken: 'x' })
      if (init?.method === 'POST') {
        llamadas.push(url)
        return json({})
      }
      if (url.includes('/por-autorizar/')) return json(porAutorizar)
      return json(tableros)
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AvisosPage />
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => vi.unstubAllGlobals())

describe('AvisosPage', () => {
  it('lista los tableros en una tabla ordenada y abre uno', async () => {
    montar({ puede_autorizar: false, avisos: [] })
    const tabla = await screen.findByRole('region', { name: 'Tus tableros de avisos' })
    await within(tabla).findByText('Grupo · Norte')
    const filas = within(tabla).getAllByRole('row').slice(1)
    expect(filas[0]).toHaveTextContent('Toda la iglesia') // la iglesia va antes que los grupos
    expect(filas[1]).toHaveTextContent('2 mensajes nuevos')
    fireEvent.click(within(filas[1]).getByRole('button', { name: 'Abrir' }))
    expect(screen.getByText('Panel de Grupo · Norte')).toBeInTheDocument()
  })

  it('quien autoriza ve los avisos pendientes y puede autorizarlos o rechazarlos', async () => {
    const llamadas = montar({ puede_autorizar: true, avisos: [pendiente] })
    const tabla = await screen.findByRole('region', { name: 'Avisos por autorizar' })
    expect(within(tabla).getByText('Convivio de la iglesia')).toBeInTheDocument()
    fireEvent.click(within(tabla).getByRole('button', { name: 'Autorizar' }))
    await waitFor(() => expect(llamadas).toContain('/api/tablero/31/autorizar/'))
  })

  it('quien lo pidió ve su aviso sin botones para resolverlo', async () => {
    montar({ puede_autorizar: false, avisos: [{ ...pendiente, puede_resolver: false }] })
    const tabla = await screen.findByRole('region', { name: 'Avisos por autorizar' })
    expect(within(tabla).getByText('Por autorizar')).toBeInTheDocument()
    expect(within(tabla).queryByRole('button', { name: 'Autorizar' })).toBeNull()
  })

  it('sin pendientes no muestra la sección', async () => {
    montar({ puede_autorizar: true, avisos: [] })
    await screen.findByRole('region', { name: 'Tus tableros de avisos' })
    expect(screen.queryByRole('region', { name: 'Avisos por autorizar' })).toBeNull()
  })
})

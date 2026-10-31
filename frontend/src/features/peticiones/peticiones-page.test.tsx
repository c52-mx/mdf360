import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PeticionesPage } from './peticiones-page'
import type { Peticion } from './types'

vi.mock('@/features/auth/use-auth', () => ({
  useAuth: () => ({ user: { id: 7, nombre: 'Ana' } }),
  useCan: () => false,
}))
vi.mock('./peticiones-panel', async (original) => ({
  ...(await original<typeof import('./peticiones-panel')>()),
  PeticionesPanel: () => null,
}))

const json = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))

const base: Peticion = {
  id: 1,
  origen: { tipo: 'grupo', tipo_display: 'Grupo de Conexión', id: 4, etiqueta: 'Grupo · Norte', referencia_id: null },
  estado: 'activa',
  estado_display: 'Activa',
  visibilidad: 'lideres',
  visibilidad_display: 'Solo líderes',
  ocultar_nombre: false,
  puede_gestionar: true,
  creada_en: '2026-10-20T10:00:00Z',
  expira_en: '2026-11-19T10:00:00Z',
  datos: { peticion: 'Por la salud de mi mamá' },
}
const peticiones: Peticion[] = [
  base,
  { ...base, id: 2, estado: 'atendida', estado_display: 'Atendida', datos: { peticion: 'Por un empleo' } },
  {
    ...base,
    id: 3,
    origen: { tipo: 'persona', tipo_display: 'Petición personal', id: 7, etiqueta: 'Petición personal', referencia_id: null },
    datos: { peticion: 'Por mi familia' },
  },
]

function montar(resultados = peticiones) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/resumen/'))
        return json({
          semanas: [
            { semana: '2026-10-12', activas: 1, atendidas: 0 },
            { semana: '2026-10-19', activas: 1, atendidas: 1 },
          ],
          totales: { activas: 2, atendidas: 1 },
          dias_retencion: 30,
        })
      if (url.includes('/formulario/'))
        return json({ version: 1, campos: [{ clave: 'peticion', etiqueta: 'Petición', tipo: 'texto', requerido: true, activo: true, opciones: [] }] })
      return json({ count: resultados.length, next: null, previous: null, results: resultados })
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <PeticionesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('PeticionesPage', () => {
  it('agrupa por canal de llegada y, dentro, por estado', async () => {
    montar()
    expect(await screen.findByRole('button', { name: /Grupo de Conexión/ })).toHaveTextContent('1 pendientes · 1 atendidas')
    expect(screen.getByRole('button', { name: /Petición personal/ })).toHaveTextContent('1 pendientes · 0 atendidas')
    // Los canales arrancan cerrados cuando hay más de uno: nada de contenido hasta consultarlo
    expect(screen.queryByText('Por la salud de mi mamá')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /Grupo de Conexión/ }))
    expect(screen.getByRole('heading', { name: 'Pendientes (1)' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Atendidas (1)' })).toBeInTheDocument()
    const pendientes = screen.getByRole('region', { name: 'Grupo de Conexión: pendientes' })
    expect(within(pendientes).getByText('Por la salud de mi mamá')).toBeInTheDocument()
    expect(within(pendientes).queryByText('Por un empleo')).toBeNull()
  })

  it('muestra la gráfica de atendidas y pendientes con sus totales', async () => {
    montar()
    expect(await screen.findByRole('img', { name: 'Peticiones recibidas por semana' })).toBeInTheDocument()
    expect(screen.getByText(/1 atendidas y 2 pendientes/)).toBeInTheDocument()
    expect(screen.getByText(/se borra a los 30 días/)).toBeInTheDocument()
  })

  it('abre el detalle de una petición en una ventana', async () => {
    montar()
    fireEvent.click(await screen.findByRole('button', { name: /Grupo de Conexión/ }))
    const pendientes = screen.getByRole('region', { name: 'Grupo de Conexión: pendientes' })
    fireEvent.click(within(pendientes).getByRole('button', { name: 'Ver' }))
    expect(screen.getByRole('dialog', { name: 'Petición de oración' })).toBeInTheDocument()
  })
})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DashboardPage } from './dashboard-page'

const datos = {
  resumen: { grupos: 2, integrantes: 9, asistencia_pct: 72, alertas: 2, asistencia_minima_pct: 60 },
  serie: [
    { semana: '2026-09-07', presentes: 0, registrados: 0, pct: null },
    { semana: '2026-09-14', presentes: 6, registrados: 8, pct: 75 },
  ],
  grupos: [
    {
      id: 1,
      nombre: 'Conexión Norte',
      integrantes: 5,
      reuniones_8_semanas: 3,
      asistencia_pct: 80,
      ultimas: [{ fecha: '2026-10-15', presentes: 4, registrados: 5 }],
      ultima_reunion: '2026-10-15',
      sin_lista_esta_semana: true,
      ofrendas: { avalado_30_dias: '1250.00', pendientes: 1, con_diferencia: 1 },
      peticiones_activas: 2,
    },
    {
      id: 2,
      nombre: 'Conexión Sur',
      integrantes: 4,
      reuniones_8_semanas: 0,
      asistencia_pct: null,
      ultimas: [],
      ultima_reunion: null,
      sin_lista_esta_semana: false,
      ofrendas: null,
      peticiones_activas: null,
    },
  ],
  alertas: [
    { tipo: 'sin_lista', grupo_id: 1, grupo: 'Conexión Norte' },
    { tipo: 'ofrenda_con_diferencia', grupo_id: 1, grupo: 'Conexión Norte', valor: 1 },
  ],
}

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

afterEach(() => vi.unstubAllGlobals())

function montar() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('DashboardPage', () => {
  it('muestra resumen, avisos y cada grupo con sus datos permitidos', async () => {
    vi.stubGlobal('fetch', vi.fn(() => json(200, datos)))
    montar()
    expect(await screen.findByText('Resumen de grupos')).toBeInTheDocument()
    expect(screen.getByText('72%')).toBeInTheDocument()
    expect(screen.getByText(/todavía no hay lista de asistencia esta semana/)).toBeInTheDocument()
    expect(screen.getByText(/1 ofrenda con diferencia/)).toBeInTheDocument()
    expect(screen.getByText('2 peticiones activas')).toBeInTheDocument()
    expect(screen.getByText('1 con diferencia')).toBeInTheDocument()
    // el grupo sin finanzas visibles ni asistencia no muestra montos y dice «Sin datos»
    expect(screen.getByText('Sin datos')).toBeInTheDocument()
    expect(screen.getAllByText(/Avalado en 30 días/)).toHaveLength(1)
    expect(screen.getByRole('list', { name: 'Asistencia por semana (todos tus grupos)' })).toBeInTheDocument()
  })

  it('dice que todo está en orden cuando no hay avisos', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => json(200, { ...datos, alertas: [], resumen: { ...datos.resumen, alertas: 0 } })),
    )
    montar()
    expect(await screen.findByText('Todo en orden: no hay avisos pendientes.')).toBeInTheDocument()
  })

  it('avisa si no hay grupos que supervisar', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        json(200, { resumen: { ...datos.resumen, grupos: 0, integrantes: 0, asistencia_pct: null, alertas: 0 }, serie: [], grupos: [], alertas: [] }),
      ),
    )
    montar()
    expect(await screen.findByText('Todavía no tienes grupos que supervisar.')).toBeInTheDocument()
  })
})

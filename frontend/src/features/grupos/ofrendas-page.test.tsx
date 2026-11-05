import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OfrendasPage } from './ofrendas-page'

const json = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const resumen = {
  filas: [
    { id: 1, origen: 'grupo', origen_display: 'Conexión Norte', fecha: '2026-10-20', tipo: 'Ofrenda regular', monto: '250.00', estado: 'avalada', estado_display: 'Avalada', concepto: '' },
    { id: 2, origen: 'iglesia', origen_display: 'Iglesia', fecha: '2026-10-25', tipo: 'Diezmo', monto: '1000.00', estado: 'pendiente', estado_display: 'Pendiente de aval', concepto: '' },
  ],
  truncado: false,
  totales: { total: '1250.00', avalado: '250.00', por_avalar: '1000.00', cantidad: 2, grupo: '250.00', iglesia: '1000.00' },
  por_tipo: [
    { tipo: 'Diezmo', monto: '1000.00' },
    { tipo: 'Ofrenda regular', monto: '250.00' },
  ],
  por_mes: [{ mes: '2026-10', grupo: '250.00', iglesia: '1000.00' }],
}
const tipos = {
  puede_administrar: true,
  tipos: [
    { id: 1, nombre: 'Ofrenda regular', para_grupo: true, para_iglesia: true, activo: true },
    { id: 3, nombre: 'Diezmo', para_grupo: false, para_iglesia: true, activo: true },
  ],
}

function servidor(extra: Record<string, unknown> = {}) {
  const llamadas: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      llamadas.push(`${init?.method ?? 'GET'} ${url}`)
      if (url.includes('/ofrendas/resumen/')) return json(resumen)
      if (url.includes('/ofrendas/tipos/')) return json(tipos)
      if (url.includes('/ofrendas/iglesia/')) return json({ puede_capturar: true })
      if (url.includes('/ofrendas/pendientes/')) return json(extra.pendientes ?? [])
      return json({}, 404)
    }),
  )
  return llamadas
}

function montar() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <OfrendasPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('Ofrendas', () => {
  it('muestra totales, tabla de movimientos con su pie y el catálogo', async () => {
    servidor()
    montar()
    const tabla = await screen.findByRole('table', { name: 'Movimientos de ofrendas' })
    expect(within(tabla).getByText('Conexión Norte')).toBeInTheDocument()
    expect(within(tabla).getByText('Iglesia')).toBeInTheDocument()
    expect(within(tabla).getByText('2 movimientos')).toBeInTheDocument()
    expect(screen.getAllByText(/1,250\.00/).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /Tipos de ofrenda/ })).toBeInTheDocument()
  })

  it('al cambiar un filtro pide el resumen con ese filtro', async () => {
    const llamadas = servidor()
    montar()
    await screen.findByRole('table', { name: 'Movimientos de ofrendas' })
    fireEvent.change(screen.getByLabelText('Origen'), { target: { value: 'iglesia' } })
    await waitFor(() => expect(llamadas.some((l) => l.includes('resumen/?origen=iglesia'))).toBe(true))
    expect(screen.getByRole('button', { name: 'Quitar filtros' })).toBeInTheDocument()
  })

  it('quien puede capturar ve el botón y el formulario trae solo tipos de la iglesia', async () => {
    const llamadas = servidor()
    montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Capturar ofrenda de la iglesia' }))
    await waitFor(() => expect(llamadas.some((l) => l.includes('tipos/?para=iglesia'))).toBe(true))
  })

  it('lista lo que está por avalar y abre el aval', async () => {
    servidor({
      pendientes: [
        { id: 2, origen: 'iglesia', fecha: '2026-10-25', grupo: 'Iglesia', tipo: 3, tipo_display: 'Diezmo', concepto: '', monto: '1000.00', estado: 'pendiente', estado_display: 'Pendiente de aval', con_diferencia: false },
      ],
    })
    montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Contar y avalar' }))
    expect(await screen.findByLabelText('Cantidad que contaste')).toBeInTheDocument()
  })
})

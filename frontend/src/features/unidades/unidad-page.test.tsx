import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '@/design-system'
import type { UnidadDetalle } from './types'
import { UnidadPage } from './unidad-page'

vi.mock('@/features/tablero/tablero-panel', () => ({ TableroPanel: () => null }))

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const unidad: UnidadDetalle = {
  id: 2,
  nombre: 'Cafetería',
  descripcion: 'Café y pan',
  activa: true,
  encargados: ['Eva Encargada'],
  integrantes: 2,
  mis_roles: ['encargado'],
  miembros: [
    { id: 1, persona_id: 1, nombre: 'Eva Encargada', rol: 'encargado', rol_display: 'Encargado' },
    { id: 2, persona_id: 2, nombre: 'Sergio Servidor', rol: 'servidor', rol_display: 'Servidor' },
  ],
  puede_gestionar: true,
  puede_administrar: false,
}

function montar(datos = unidad, llamadas: { url: string; init?: RequestInit }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method && init.method !== 'GET') {
        llamadas.push({ url, init })
        return json(200, {})
      }
      return json(200, datos)
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/unidades/2']}>
          <Routes>
            <Route path="/unidades/:id" element={<UnidadPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => vi.unstubAllGlobals())

describe('UnidadPage', () => {
  it('el encargado maneja servidores pero no puede cambiar ni asignar encargados', async () => {
    montar()
    expect(await screen.findByText('Sergio Servidor')).toBeInTheDocument()
    expect(screen.getByLabelText('Rol de Sergio Servidor')).toBeInTheDocument()
    // el otro encargado no se puede tocar sin la administración de unidades
    expect(screen.queryByLabelText('Rol de Eva Encargada')).toBeNull()
    const opciones = Array.from(
      (screen.getByLabelText('Rol en la unidad') as HTMLSelectElement).options,
    ).map((o) => o.value)
    expect(opciones).toEqual(['servidor'])
    expect(screen.queryByText('Datos de la unidad')).toBeNull()
  })

  it('la administración ve todos los roles y edita los datos', async () => {
    montar({ ...unidad, puede_administrar: true })
    await screen.findByText('Sergio Servidor')
    const opciones = Array.from(
      (screen.getByLabelText('Rol en la unidad') as HTMLSelectElement).options,
    ).map((o) => o.value)
    expect(opciones).toEqual(['servidor', 'respaldo', 'encargado'])
    expect(screen.getByText('Datos de la unidad')).toBeInTheDocument()
  })

  it('agrega a una persona con su rol y permite deshacer al quitarla', async () => {
    const llamadas = montar()
    fireEvent.change(await screen.findByLabelText('WhatsApp'), { target: { value: '5590000001' } })
    fireEvent.change(screen.getByLabelText('Nombre (si es nueva)'), { target: { value: 'Vecina' } })
    fireEvent.click(screen.getByRole('button', { name: 'Agregar' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/unidades/2/integrantes/'))
    fireEvent.click(screen.getAllByRole('button', { name: 'Quitar' })[0])
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/unidades/2/integrantes/2/'))
    fireEvent.click(await screen.findByRole('button', { name: 'Deshacer' }))
    await waitFor(() =>
      expect(llamadas.map((l) => l.url)).toContain('/api/unidades/2/integrantes/2/restaurar/'),
    )
  })
})

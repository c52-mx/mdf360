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

const rol = (clave: string, nombre: string, de_gestion: boolean) => ({
  ambito: 'ministerio', clave, nombre, descripcion: '', permisos: [], activo: true, es_base: true, en_uso: 0, de_gestion,
})
const roles = [rol('servidor', 'Servidor', false), rol('respaldo', 'Respaldo', true), rol('encargado', 'Encargado', true)]

function montar(datos = unidad, llamadas: { url: string; init?: RequestInit }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method && init.method !== 'GET') {
        llamadas.push({ url, init })
        return json(200, {})
      }
      if (url.includes('/roles-equipo/')) return json(200, roles)
      return json(200, datos)
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/ministerios/2']}>
          <Routes>
            <Route path="/ministerios/:id" element={<UnidadPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
  return llamadas
}

const opciones = () =>
  Array.from((screen.getByLabelText('Rol en el ministerio') as HTMLSelectElement).options).map(
    (o) => o.value,
  )

afterEach(() => vi.unstubAllGlobals())

describe('UnidadPage', () => {
  it('el encargado maneja servidores pero no puede cambiar ni asignar encargados', async () => {
    montar()
    expect(await screen.findByText('Sergio Servidor')).toBeInTheDocument()
    expect(screen.getByLabelText('Rol de Sergio Servidor')).toBeInTheDocument()
    // el otro encargado no se puede tocar sin la administración de ministerios
    expect(screen.queryByLabelText('Rol de Eva Encargada')).toBeNull()
    await waitFor(() => expect(opciones()).toEqual(['servidor']))
    expect(screen.queryByText('Datos del ministerio')).toBeNull()
  })

  it('la administración ve todos los roles y edita los datos', async () => {
    montar({ ...unidad, puede_administrar: true })
    await screen.findByText('Sergio Servidor')
    await waitFor(() => expect(opciones()).toEqual(['servidor', 'respaldo', 'encargado']))
    expect(screen.getByText('Datos del ministerio')).toBeInTheDocument()
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

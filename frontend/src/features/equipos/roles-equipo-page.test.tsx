import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '@/design-system'
import { RolesEquipoPage } from './roles-equipo-page'
import type { RolEquipo } from './use-roles-equipo'

vi.mock('@/features/auth/use-auth', () => ({ useCan: () => true }))

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const rol = (clave: string, nombre: string, permisos: string[], es_base = true): RolEquipo => ({
  ambito: 'ministerio',
  clave,
  nombre,
  descripcion: '',
  permisos,
  activo: true,
  es_base,
  en_uso: 0,
  de_gestion: permisos.includes('integrantes'),
})

const roles = [
  rol('encargado', 'Encargado', ['ver', 'integrantes', 'avisos']),
  rol('servidor', 'Servidor', ['ver']),
]
const catalogo = [
  { codigo: 'ver', accion: 'Consultar el ministerio y su gente', pantalla: 'Su ministerio', sensible: false },
  { codigo: 'integrantes', accion: 'Agregar, cambiar y quitar servidores', pantalla: 'Su ministerio', sensible: false },
  { codigo: 'avisos', accion: 'Publicar avisos en el tablero del ministerio', pantalla: 'Tablero', sensible: false },
]

function montar(llamadas: { url: string; init?: RequestInit }[] = []) {
  const pedidos: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method && init.method !== 'GET') {
        llamadas.push({ url, init })
        return json(200, rol('nuevo', 'Coordinador', ['ver'], false))
      }
      pedidos.push(url)
      return json(200, url.includes('/permisos-equipo/') ? catalogo : roles)
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>
        <MemoryRouter>
          <RolesEquipoPage />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
  return { llamadas, pedidos }
}

afterEach(() => vi.unstubAllGlobals())

describe('RolesEquipoPage', () => {
  it('lista los roles base y deja cambiar de ministerios a grupos', async () => {
    const { pedidos } = montar()
    expect(await screen.findByText('Encargado')).toBeInTheDocument()
    expect(screen.getByText('Servidor')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Grupos de Conexión' }))
    await waitFor(() => expect(pedidos.some((u) => u.includes('ambito=grupo'))).toBe(true))
  })

  it('crea un rol nuevo con las acciones marcadas', async () => {
    const { llamadas } = montar()
    await screen.findByText('Encargado')
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo rol' }))
    fireEvent.change(await screen.findByLabelText('Nombre'), { target: { value: 'Coordinador' } })
    fireEvent.click(await screen.findByLabelText('Publicar avisos en el tablero del ministerio'))
    fireEvent.click(screen.getByRole('button', { name: 'Guardar rol' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/auth/roles-equipo/'))
    expect(JSON.parse(String(llamadas[0].init?.body))).toEqual({
      nombre: 'Coordinador',
      descripcion: '',
      permisos: ['avisos'],
      ambito: 'ministerio',
    })
  })

  it('edita los permisos de un rol base pero no permite desactivarlo', async () => {
    const { llamadas } = montar()
    fireEvent.click((await screen.findAllByRole('button', { name: 'Editar' }))[1])
    fireEvent.click(await screen.findByLabelText('Agregar, cambiar y quitar servidores'))
    expect(screen.queryByRole('button', { name: 'Desactivar' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar rol' }))
    await waitFor(() =>
      expect(llamadas.map((l) => l.url)).toContain('/api/auth/roles-equipo/ministerio/servidor/'),
    )
    expect(JSON.parse(String(llamadas[0].init?.body)).permisos.sort()).toEqual(['integrantes', 'ver'])
  })
})

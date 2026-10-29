import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '@/design-system'
import { PermisosPage, type Catalogo, type RolCompleto } from './permisos-page'

vi.mock('./use-auth', () => ({
  useCan: () => true,
  useAuth: () => ({
    user: { roles: ['secretaria'], permisos: ['personas.crear', 'roles.administrar'] },
  }),
}))

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const rol = (r: Partial<RolCompleto> & Pick<RolCompleto, 'clave' | 'nombre' | 'nivel'>): RolCompleto => ({
  descripcion: '',
  permisos: [],
  exige_credencial_fuerte: false,
  activo: true,
  es_base: false,
  editable: true,
  usuarios: 0,
  ...r,
})

const roles = [
  rol({ clave: 'admin_tecnico', nombre: 'Administrador Técnico', nivel: 0, editable: false, es_base: true }),
  rol({ clave: 'secretaria', nombre: 'Secretaria', nivel: 1, editable: false, es_base: true, usuarios: 1 }),
  rol({ clave: 'lider', nombre: 'Líder / Maestro', nivel: 4, es_base: true, permisos: ['personas.crear'] }),
  rol({ clave: 'temporal', nombre: 'Temporal', nivel: 6 }),
]

const catalogo: Catalogo[] = [
  {
    modulo: 'Personas',
    pantallas: [
      {
        pantalla: 'Expedientes',
        acciones: [
          { codigo: 'personas.ver', accion: 'Ver expedientes', sensible: true },
          { codigo: 'personas.crear', accion: 'Registrar contactos', sensible: false },
        ],
      },
    ],
  },
]

function montar(llamadas: { url: string; init?: RequestInit }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method && init.method !== 'GET') {
        llamadas.push({ url, init })
        return json(200, rol({ clave: 'nuevo-rol', nombre: 'Encargado', nivel: 6 }))
      }
      return json(200, url.includes('/permisos/') ? catalogo : roles)
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>
        <MemoryRouter>
          <PermisosPage />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => vi.unstubAllGlobals())

describe('PermisosPage', () => {
  it('lista los roles y deja consultar, pero no cambiar, los de su nivel o superiores', async () => {
    montar()
    expect(await screen.findByText('Administrador Técnico')).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('button', { name: 'Ver' })[0])
    expect(await screen.findByText(/puedes consultarlo, pero no cambiarlo/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Guardar rol' })).toBeNull()
  })

  it('crea un rol marcando acciones, y no deja conceder las que no se tienen', async () => {
    const llamadas = montar()
    await screen.findByText('Administrador Técnico') // espera a conocer los roles (y mi nivel)
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo rol' }))
    expect(await screen.findByText('Personas')).toBeInTheDocument()
    // «Ver expedientes» es sensible y la secretaria de la prueba no lo tiene
    expect(screen.getByRole('checkbox', { name: 'Ver expedientes' })).toBeDisabled()
    expect(screen.getByText('Sensible')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Encargado' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'Registrar contactos' }))
    fireEvent.click(screen.getByRole('button', { name: 'Guardar rol' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/auth/roles/'))
    expect(JSON.parse(String(llamadas[0].init?.body))).toMatchObject({
      nombre: 'Encargado',
      nivel: 2,
      permisos: ['personas.crear'],
    })
  })

  it('un rol base no ofrece desactivarse, uno propio sí, con confirmación', async () => {
    const llamadas = montar()
    const filas = await screen.findAllByRole('button', { name: 'Editar' })
    fireEvent.click(filas[0]) // Líder (base)
    expect(await screen.findByRole('button', { name: 'Guardar rol' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Desactivar' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Volver al listado' }))
    fireEvent.click((await screen.findAllByRole('button', { name: 'Editar' }))[1]) // Temporal
    fireEvent.click(await screen.findByRole('button', { name: 'Desactivar' }))
    expect(llamadas).toEqual([])
    fireEvent.click(screen.getByRole('button', { name: 'Sí, desactivar' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/auth/roles/temporal/desactivar/'))
  })

  it('duplicar crea una copia y abre su edición', async () => {
    const llamadas = montar()
    fireEvent.click((await screen.findAllByRole('button', { name: 'Editar' }))[0])
    fireEvent.click(await screen.findByRole('button', { name: 'Duplicar' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/auth/roles/lider/duplicar/'))
  })
})

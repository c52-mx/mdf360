import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RolesPage } from './roles-page'

vi.mock('./use-auth', () => ({ useCan: () => true }))

const json = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))

const roles = [
  { clave: 'lider', nombre: 'Líder / Maestro', nivel: 4 },
  { clave: 'miembro', nombre: 'Miembro / Asistente', nivel: 7 },
]
const usuario = (id: number, nombre: string, rolesDe: string[]) => ({
  id,
  nombre,
  whatsapp: `+52550000000${id}`,
  email: '',
  requires_strong_credential: false,
  roles: rolesDe,
  permisos: [],
})
const usuarios = [usuario(1, 'Ana Líder', ['lider']), usuario(2, 'Beto Nuevo', [])]

afterEach(() => vi.unstubAllGlobals())

describe('RolesPage', () => {
  it('lista en una tabla con el rol de cada quien y permite volver al listado', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => json(url.includes('/permisos/') ? [] : url.includes('/roles/') ? roles : usuarios)),
    )
    render(
      <QueryClientProvider client={new QueryClient()}>
        <RolesPage />
      </QueryClientProvider>,
    )
    const tabla = await screen.findByRole('table', { name: 'Personas con acceso y sus roles' })
    expect(tabla).toHaveTextContent('Líder / Maestro')
    expect(tabla).toHaveTextContent('Sin rol')
    fireEvent.click(screen.getAllByRole('button', { name: 'Asignar roles' })[1])
    expect(await screen.findByRole('checkbox', { name: 'Miembro / Asistente' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Volver al listado' }))
    expect(
      await screen.findByRole('table', { name: 'Personas con acceso y sus roles' }),
    ).toBeInTheDocument()
  })
})

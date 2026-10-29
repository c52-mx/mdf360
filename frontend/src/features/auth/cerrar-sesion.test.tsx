import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { RequireAuth } from './require-auth'
import { AuthProvider, useAuth } from './use-auth'

vi.mock('@/lib/push', () => ({ quitarDispositivo: () => Promise.resolve() }))

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const yo = { id: 1, nombre: 'Ana', whatsapp: '1', email: '', requires_strong_credential: false, roles: [], permisos: [] }

function Pantalla() {
  const { logout } = useAuth()
  // una consulta abierta, como la lista de grupos: no debe verse fallar al cerrar sesión
  const datos = useQuery({ queryKey: ['grupos'], queryFn: () => fetch('/api/grupos/').then((r) => r.json()) })
  return (
    <div>
      <p>Privada {datos.isError ? 'con error' : ''}</p>
      <button onClick={() => void logout()}>Cerrar sesión</button>
    </div>
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('cerrar sesión', () => {
  it('lleva al login aunque el servidor ya no reconozca la sesión', async () => {
    let cerrada = false
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url.includes('/logout/')) {
          cerrada = true
          return json(403, { detail: 'Las credenciales de autenticación no se proveyeron.' })
        }
        if (url.includes('/auth/me/')) return cerrada ? json(403, {}) : json(200, yo)
        return init ? json(200, {}) : json(200, [])
      }),
    )
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/']}>
            <Routes>
              <Route path="/login" element={<p>Pantalla de acceso</p>} />
              <Route element={<RequireAuth />}>
                <Route path="/" element={<Pantalla />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    )
    fireEvent.click(await screen.findByRole('button', { name: 'Cerrar sesión' }))
    expect(await screen.findByText('Pantalla de acceso')).toBeInTheDocument()
    await waitFor(() => expect(screen.queryByText(/con error/)).toBeNull())
  })
})

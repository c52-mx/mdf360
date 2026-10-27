import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '@/features/auth/use-auth'
import { pendientes } from '@/lib/outbox'
import { ListaSinConexionPage } from './lista-sin-conexion-page'

const usuario = {
  id: 4,
  nombre: 'Sara',
  whatsapp: '+525500000004',
  email: '',
  requires_strong_credential: false,
  roles: ['secretario'],
  permisos: [],
}
const grupo = {
  id: 3,
  nombre: 'Conexión Norte',
  tipo: 'conexion',
  sector: '',
  colonia: '',
  dia_semana: 3,
  dia: 'Jueves',
  hora: '19:30',
  lideres: [],
  integrantes: 2,
  mis_roles: ['secretario'],
  ofrendas_con_diferencia: null,
  miembros: [
    { id: 1, persona_id: 10, nombre: 'Ana Martínez', rol: 'asistente', rol_display: 'Asistente', invitado: false },
    { id: 2, persona_id: 11, nombre: 'Sofía Cruz', rol: 'asistente', rol_display: 'Asistente', invitado: true },
    { id: 3, persona_id: 10, nombre: 'Ana Martínez', rol: 'anfitrion', rol_display: 'Anfitrión', invitado: false },
  ],
  reuniones: [],
  puede_capturar: true,
  puede_gestionar: false,
  puede_administrar: false,
}

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

beforeEach(() => localStorage.clear())

describe('ListaSinConexionPage', () => {
  it('arma la lista con el grupo guardado, sin repetir personas, y deja la captura en cola', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/auth/me/')) return json(200, usuario)
        if (url.includes('/api/grupos/3/')) return json(200, grupo)
        return json(404, {})
      }),
    )
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/grupos/3/hoy']}>
            <Routes>
              <Route path="/grupos/:id/hoy" element={<ListaSinConexionPage />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('Sofía Cruz')).toBeInTheDocument()
    expect(screen.getAllByText('Ana Martínez')).toHaveLength(1) // Ana aparece con dos roles
    expect(screen.getByText('0 de 2 presentes')).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('checkbox')[0])
    fireEvent.click(screen.getByRole('button', { name: 'Guardar lista' }))
    expect(await screen.findByText(/quedó guardada en tu teléfono/)).toBeInTheDocument()
    await waitFor(() => expect(pendientes.listar(4)).toHaveLength(1))
    const guardada = pendientes.listar(4)[0]
    expect(guardada).toMatchObject({ grupoId: 3, grupoNombre: 'Conexión Norte' })
    expect(guardada.reunionId).toBeUndefined() // la reunión se abre al sincronizar
    expect(guardada.asistencias).toEqual([
      { persona_id: 10, presente: true },
      { persona_id: 11, presente: false },
    ])
    expect(guardada.capturadoEn).toMatch(/^\d{4}-\d{2}-\d{2}T/)
  })

  it('explica qué hacer si el grupo nunca se abrió con conexión', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => (url.includes('/auth/me/') ? json(200, usuario) : Promise.reject(new TypeError('sin red')))),
    )
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/grupos/3/hoy']}>
            <Routes>
              <Route path="/grupos/:id/hoy" element={<ListaSinConexionPage />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>,
    )
    expect(await screen.findByText(/todavía no está guardado en tu teléfono/)).toBeInTheDocument()
  })
})

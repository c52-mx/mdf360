import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '@/features/auth/use-auth'
import { pendientes } from '@/lib/outbox'
import { ReunionPage } from './reunion-page'

const reunion = {
  id: 5,
  fecha: '2026-10-22',
  notas: '',
  grupo: { id: 1, nombre: 'Conexión Norte' },
  personas: [
    { persona_id: 1, nombre: 'Ana Martínez', roles: ['asistente'], invitado: false, presente: false, registrada: false },
    { persona_id: 2, nombre: 'Sofía Cruz', roles: ['asistente'], invitado: true, presente: false, registrada: false },
  ],
  estudio: {
    id: 1,
    semana: '2026-10-19',
    titulo: 'Lección 4',
    pdf_adultos: '/api/grupos/estudios/1/archivo/pdf_adultos/',
    pdf_ninos: null,
    audio: '/api/grupos/estudios/1/archivo/audio/',
  },
  puede_modificar: true,
}

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const usuario = {
  id: 4,
  nombre: 'Sara',
  whatsapp: '+525500000004',
  email: '',
  requires_strong_credential: false,
  roles: ['secretario'],
  permisos: [],
}

afterEach(() => {
  vi.unstubAllGlobals()
  localStorage.clear()
})

function montar() {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>
        <MemoryRouter initialEntries={['/grupos/reuniones/5']}>
          <Routes>
            <Route path="/grupos/reuniones/:rid" element={<ReunionPage />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

describe('ReunionPage', () => {
  it('marca presentes, cuenta y guarda la lista', async () => {
    const put = vi.fn(() => json(200, { presentes: 2 }))
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/auth/me/')) return json(200, usuario)
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url.includes('/ofrendas/')) return json(404, {})
        if (url.includes('/peticiones/')) return json(403, {})
        if (init?.method === 'PUT') return put()
        return json(200, reunion)
      }),
    )
    montar()
    expect(await screen.findByText('Lección 4')).toBeInTheDocument()
    expect(screen.getByText('Invitado')).toBeInTheDocument()
    expect(screen.getByText('0 de 2 presentes')).toBeInTheDocument()
    const botones = screen.getAllByRole('checkbox')
    fireEvent.click(botones[0])
    fireEvent.click(botones[1])
    expect(screen.getByText('2 de 2 presentes')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar lista' }))
    await waitFor(() => expect(put).toHaveBeenCalled())
    expect(await screen.findByText('Lista guardada.')).toBeInTheDocument()
  })

  it('sin conexión deja la lista guardada en el teléfono para enviarla después', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/auth/me/')) return json(200, usuario)
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (url.includes('/ofrendas/')) return json(404, {})
        if (url.includes('/peticiones/')) return json(403, {})
        if (init?.method === 'PUT') return Promise.reject(new TypeError('Failed to fetch'))
        return json(200, reunion)
      }),
    )
    montar()
    fireEvent.click((await screen.findAllByRole('checkbox'))[0])
    fireEvent.click(screen.getByRole('button', { name: 'Guardar lista' }))
    expect(await screen.findByText(/quedó guardada en tu teléfono/)).toBeInTheDocument()
    await waitFor(() => expect(pendientes.listar(4)).toHaveLength(1))
    expect(pendientes.listar(4)[0]).toMatchObject({ reunionId: 5, grupoId: 1, fecha: '2026-10-22' })
    expect(pendientes.listar(4)[0].asistencias).toEqual([
      { persona_id: 1, presente: true },
      { persona_id: 2, presente: false },
    ])
  })
})

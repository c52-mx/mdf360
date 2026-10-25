import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
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

afterEach(() => vi.unstubAllGlobals())

describe('ReunionPage', () => {
  it('marca presentes, cuenta y guarda la lista', async () => {
    const put = vi.fn(() => json(200, { presentes: 2 }))
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (init?.method === 'PUT') return put()
        return json(200, reunion)
      }),
    )
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={['/grupos/reuniones/5']}>
          <Routes>
            <Route path="/grupos/reuniones/:rid" element={<ReunionPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(await screen.findByText('Lección 4')).toBeInTheDocument()
    expect(screen.getByText('Invitado')).toBeInTheDocument()
    expect(screen.getByText('0 de 2 presentes')).toBeInTheDocument()
    const botones = screen.getAllByRole('button', { name: 'Ausente' })
    fireEvent.click(botones[0])
    fireEvent.click(botones[1])
    expect(screen.getByText('2 de 2 presentes')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar lista' }))
    await waitFor(() => expect(put).toHaveBeenCalled())
    expect(await screen.findByText('Lista guardada.')).toBeInTheDocument()
  })
})

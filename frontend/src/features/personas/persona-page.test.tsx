import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PersonaPage } from './persona-page'
import type { Movimiento, Persona } from './types'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const persona = {
  id: 5,
  roles: ['Líder / Maestro'],
  nivel: 'contacto',
  procedencia: 'visitante',
  activo: true,
  nombre: 'Gloria',
  apellido_paterno: 'Ríos',
  apellido_materno: '',
  nombre_completo: 'Gloria Ríos',
  edad: null,
  tiene_foto: false,
  faltantes_edu: ['fecha de nacimiento'],
  procesos: [],
  actualizado_en: '2026-10-27T10:00:00Z',
} as unknown as Persona

const movimientos: Movimiento[] = [
  {
    id: 1,
    tipo: 'traslado',
    tipo_display: 'Traslado a otra iglesia',
    fecha: '2026-10-01',
    motivo: '',
    iglesia_destino: 'Vida Nueva',
  },
]

function montar(llamadas: { url: string; init?: RequestInit }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method === 'POST') {
        llamadas.push({ url, init })
        return json(200, { ...persona, activo: false })
      }
      if (url.includes('/movimientos/')) return json(200, movimientos)
      return json(200, persona)
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={['/personas/5']}>
        <Routes>
          <Route path="/personas/:id" element={<PersonaPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => vi.unstubAllGlobals())

describe('PersonaPage', () => {
  it('explica cada nivel de registro y qué falta para el siguiente', async () => {
    montar()
    expect(await screen.findByText('Nivel de registro')).toBeInTheDocument()
    expect(screen.getByText(/Expediente digital completo \(EDU\)/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Subir a participante' })).toBeInTheDocument()
    expect(screen.getByText('Líder / Maestro')).toBeInTheDocument()
  })

  it('muestra el destino de un traslado en el historial', async () => {
    montar()
    expect(await screen.findByText('→ Vida Nueva')).toBeInTheDocument()
  })

  it('pasa a la persona a otra iglesia con su destino', async () => {
    const llamadas = montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Pasar a otra iglesia' }))
    const confirmar = screen.getByRole('button', { name: 'Confirmar traslado' })
    expect(confirmar).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Iglesia a la que se traslada'), {
      target: { value: 'Iglesia Vida Nueva' },
    })
    fireEvent.click(confirmar)
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/personas/5/traslado/'))
    expect(JSON.parse(String(llamadas[0].init?.body)).iglesia_destino).toBe('Iglesia Vida Nueva')
  })

  it('la baja avisa que también saca a la persona de sus grupos', async () => {
    montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Dar de baja' }))
    expect(screen.getByText(/saca a la persona de sus grupos/)).toBeInTheDocument()
  })
})

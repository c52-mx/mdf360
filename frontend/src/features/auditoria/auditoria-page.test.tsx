import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AuditoriaPage } from './auditoria-page'

vi.mock('@/features/auth/use-auth', () => ({ useCan: () => true }))

const json = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))

const evento = (id: number, accion: string, nivel: string) => ({
  id,
  fecha: '2026-10-27T15:00:00Z',
  accion,
  nivel,
  actor: 'Ana',
  objeto: '',
  detalle: {},
  ip: null,
})

afterEach(() => vi.unstubAllGlobals())

describe('AuditoriaPage', () => {
  it('muestra el semáforo, la gráfica y filtra por nivel', async () => {
    const urls: string[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        urls.push(url)
        if (url.includes('/resumen/')) {
          return json({
            dias: [
              { fecha: '2026-10-26', errores: 1, avisos: 2 },
              { fecha: '2026-10-27', errores: 0, avisos: 0 },
            ],
            modulos: ['auth', 'persona'],
          })
        }
        return json({
          count: 3,
          next: null,
          previous: null,
          results: [
            evento(3, 'auth.locked', 'error'),
            evento(2, 'auth.login_failed', 'aviso'),
            evento(1, 'auth.login', 'info'),
          ],
        })
      }),
    )
    render(
      <QueryClientProvider client={new QueryClient()}>
        <AuditoriaPage />
      </QueryClientProvider>,
    )
    expect(await screen.findByText('auth.locked')).toBeInTheDocument()
    const tabla = screen.getByRole('table', { name: 'Eventos de la bitácora' })
    expect(tabla).toHaveTextContent('Error')
    expect(tabla).toHaveTextContent('Aviso')
    expect(tabla).toHaveTextContent('Informativo')
    expect(
      screen.getByRole('list', { name: 'Errores y avisos por día (últimos 14 días)' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Página 1 de 1')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Nivel'), { target: { value: 'error' } })
    await waitFor(() => expect(urls.some((u) => u.includes('nivel=error'))).toBe(true))
  })
})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MisVehiculosCard } from './mis-vehiculos-card'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const auto = {
  id: 7,
  tipo: 'auto',
  tipo_display: 'Auto',
  marca: 'Nissan',
  modelo: 'Versa',
  anio: 2020,
  color: 'Gris',
  placas: 'ABC123',
}

function montar(llamadas: { url: string; init?: RequestInit }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method && init.method !== 'GET') {
        llamadas.push({ url, init })
        return json(init.method === 'DELETE' ? 204 : 200, init.method === 'DELETE' ? null : auto)
      }
      return json(200, [auto])
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MisVehiculosCard />
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => vi.unstubAllGlobals())

describe('MisVehiculosCard', () => {
  it('lista sus vehículos y registra uno nuevo', async () => {
    const llamadas = montar()
    expect(await screen.findByText(/Auto Nissan Versa/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Marca'), { target: { value: 'Honda' } })
    fireEvent.change(screen.getByLabelText('Placas'), { target: { value: 'xyz 987' } })
    fireEvent.click(screen.getByRole('button', { name: 'Agregar vehículo' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/personas/mi-perfil/vehiculos/'))
    expect(llamadas[0].init?.method).toBe('POST')
    expect(JSON.parse(String(llamadas[0].init?.body))).toMatchObject({ marca: 'Honda', placas: 'xyz 987', anio: null })
  })

  it('edita y quita un vehículo propio', async () => {
    const llamadas = montar()
    fireEvent.click(await screen.findByRole('button', { name: 'Editar Auto Nissan Versa' }))
    fireEvent.change(screen.getByLabelText('Color'), { target: { value: 'Rojo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/personas/mi-perfil/vehiculos/7/'))
    expect(llamadas[0].init?.method).toBe('PATCH')
    fireEvent.click(screen.getByRole('button', { name: 'Quitar' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Sí, quitar' }))
    await waitFor(() => expect(llamadas.some((l) => l.init?.method === 'DELETE')).toBe(true))
  })
})

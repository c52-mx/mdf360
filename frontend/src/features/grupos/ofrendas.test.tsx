import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AvalForm, type Ofrenda } from './ofrendas'

const ofrenda: Ofrenda = {
  id: 9,
  reunion_id: 1,
  fecha: '2026-10-22',
  grupo: 'Conexión Norte',
  tipo: 'regular',
  tipo_display: 'Ofrenda regular',
  concepto: '',
  monto: '1250.00',
  estado: 'pendiente',
  estado_display: 'Pendiente de aval',
  con_diferencia: false,
}

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

afterEach(() => vi.unstubAllGlobals())

function montar(onListo = () => {}) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AvalForm ofrenda={ofrenda} onListo={onListo} />
    </QueryClientProvider>,
  )
}

describe('AvalForm', () => {
  it('avisa si la cifra coincide o si hay diferencia antes de avalar', () => {
    montar()
    const campo = screen.getByLabelText('Cantidad que contaste')
    fireEvent.change(campo, { target: { value: '1250' } })
    expect(screen.getByText('La cifra coincide con la capturada.')).toBeInTheDocument()
    fireEvent.change(campo, { target: { value: '1200' } })
    expect(screen.getByText(/Hay una diferencia/)).toBeInTheDocument()
  })

  it('envía la cifra y el PIN, y avisa al terminar', async () => {
    const aval = vi.fn(() => json(200, ofrenda))
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (init?.method === 'POST') return aval()
        return json(404, {})
      }),
    )
    const listo = vi.fn()
    montar(listo)
    fireEvent.change(screen.getByLabelText('Cantidad que contaste'), { target: { value: '1250' } })
    fireEvent.change(screen.getByLabelText('Escribe tu PIN para avalar'), { target: { value: '482915' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avalar cifra' }))
    await waitFor(() => expect(listo).toHaveBeenCalled())
    expect(aval).toHaveBeenCalledTimes(1)
  })

  it('muestra el error si el PIN es incorrecto', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (init?.method === 'POST') return json(400, { code: 'invalid_pin', detail: 'El PIN no es correcto.' })
        return json(404, {})
      }),
    )
    montar()
    fireEvent.change(screen.getByLabelText('Cantidad que contaste'), { target: { value: '1250' } })
    fireEvent.change(screen.getByLabelText('Escribe tu PIN para avalar'), { target: { value: '000001' } })
    fireEvent.click(screen.getByRole('button', { name: 'Avalar cifra' }))
    expect(await screen.findByText('El PIN no es correcto.')).toBeInTheDocument()
  })
})

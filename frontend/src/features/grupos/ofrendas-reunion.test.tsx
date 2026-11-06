import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OfrendasReunion } from './ofrendas'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const tipos = {
  puede_administrar: false,
  tipos: [
    { id: 1, nombre: 'Ofrenda regular', para_grupo: true, para_iglesia: true, activo: true },
    { id: 2, nombre: 'Ofrenda especial', para_grupo: true, para_iglesia: true, activo: true },
    { id: 3, nombre: 'Misiones', para_grupo: true, para_iglesia: false, activo: true },
  ],
}

function montar(cuerpos: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method && init.method !== 'GET') {
        cuerpos.push(JSON.parse(String(init.body)))
        return json(201, {})
      }
      if (url.includes('/ofrendas/tipos/')) return json(200, tipos)
      return json(200, { ofrendas: [], puede_capturar: true, puede_avalar: false })
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <OfrendasReunion reunionId={7} />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('OfrendasReunion', () => {
  it('ofrece todos los tipos del catálogo para grupos y captura con el elegido', async () => {
    const cuerpos: unknown[] = []
    montar(cuerpos)
    const tipo = (await screen.findByLabelText('Tipo')) as HTMLSelectElement
    await waitFor(() => expect(Array.from(tipo.options).map((o) => o.text)).toEqual(['Ofrenda regular', 'Ofrenda especial', 'Misiones']))
    fireEvent.change(tipo, { target: { value: '3' } })
    expect(screen.getByLabelText('Nota (opcional)')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Monto'), { target: { value: '120' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar ofrenda' }))
    await waitFor(() => expect(cuerpos).toEqual([{ tipo_ofrenda: 3, concepto: '', monto: '120' }]))
  })

  it('la ofrenda especial sigue pidiendo concepto', async () => {
    montar([])
    const tipo = (await screen.findByLabelText('Tipo')) as HTMLSelectElement
    await waitFor(() => expect(tipo.options.length).toBe(3))
    fireEvent.change(tipo, { target: { value: '2' } })
    expect(screen.getByLabelText('Concepto')).toBeRequired()
  })
})

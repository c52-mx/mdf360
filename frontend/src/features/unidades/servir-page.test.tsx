import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ServirPage } from './servir-page'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

function montar(token = 'tok', llamadas: { url: string; init?: RequestInit }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (url.includes('/aviso-privacidad/')) return json(200, { version: '1', texto: 'Aviso' })
      if (init?.method === 'POST') {
        llamadas.push({ url, init })
        return json(201, { ministerio: 'Cafetería' })
      }
      if (token === 'malo') return json(404, { code: 'invalid_link', detail: 'Este enlace ya no es válido.' })
      return json(200, { ministerio: 'Cafetería', descripcion: '' })
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={[`/servir/${token}`]}>
        <Routes>
          <Route path="/servir/:token" element={<ServirPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => vi.unstubAllGlobals())

describe('ServirPage', () => {
  it('quien escanea el QR se suma sin esperar aprobación', async () => {
    const llamadas = montar()
    expect(await screen.findByText('Servir en Cafetería')).toBeInTheDocument()
    const boton = screen.getByRole('button', { name: 'Sumarme al equipo' })
    expect(boton).toBeDisabled() // exige el aviso de privacidad
    fireEvent.change(screen.getByLabelText('Tu nombre'), { target: { value: 'Nora' } })
    fireEvent.change(screen.getByLabelText('Tu WhatsApp'), { target: { value: '55 7777 0001' } })
    fireEvent.click(screen.getByLabelText('Acepto el aviso de privacidad'))
    fireEvent.click(boton)
    expect(await screen.findByText(/Ya eres parte de Cafetería/)).toBeInTheDocument()
    await waitFor(() => expect(llamadas[0].url).toBe('/api/unidades/enlace/tok/sumarse/'))
    expect(JSON.parse(String(llamadas[0].init?.body))).toEqual({
      nombre: 'Nora',
      whatsapp: '55 7777 0001',
      acepta_datos: true,
    })
  })

  it('un enlace que ya no sirve lo dice', async () => {
    montar('malo')
    expect(await screen.findByText('Enlace no válido')).toBeInTheDocument()
  })
})

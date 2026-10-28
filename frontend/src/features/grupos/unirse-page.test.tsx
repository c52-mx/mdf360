import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { UnirsePage } from './unirse-page'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

function montar(respuestas: Record<string, () => Promise<Response>>) {
  const llamadas: { url: string; init?: RequestInit }[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      llamadas.push({ url, init })
      if (url.includes('/aviso-privacidad/')) return json(200, { version: '1', texto: 'Aviso genérico' })
      const clave = Object.keys(respuestas).find((k) => url.includes(k))
      return clave ? respuestas[clave]() : json(404, { detail: 'no' })
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={['/unirse/abc']}>
        <Routes>
          <Route path="/unirse/:token" element={<UnirsePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return llamadas
}

const info = () => json(200, { grupo: 'Conexión Norte', dia: 'Jueves', hora: '19:00' })

beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

describe('UnirsePage', () => {
  it('dice que el enlace ya no sirve cuando fue desactivado', async () => {
    montar({ '/enlace/abc/': () => json(404, { code: 'invalid_link', detail: 'Este enlace ya no es válido.' }) })
    expect(await screen.findByText('Enlace no válido')).toBeInTheDocument()
  })

  it('pide los datos, exige el aviso de privacidad y deja a la persona en la sala de espera', async () => {
    const llamadas = montar({
      '/solicitar/': () => json(201, { codigo: 'secreto', estado: 'pendiente', grupo: 'Conexión Norte' }),
      '/solicitudes/secreto/': () => json(200, { estado: 'pendiente', grupo: 'Conexión Norte' }),
      '/enlace/abc/': info,
    })
    expect(await screen.findByText('Unirte a Conexión Norte')).toBeInTheDocument()
    const boton = screen.getByRole('button', { name: 'Pedir mi ingreso' })
    expect(boton).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Tu nombre'), { target: { value: 'Vecina Nueva' } })
    fireEvent.change(screen.getByLabelText('Tu WhatsApp'), { target: { value: '5570000001' } })
    fireEvent.click(screen.getByLabelText('Acepto el aviso de privacidad'))
    fireEvent.click(boton)
    expect(await screen.findByText(/Espera a que tu líder te apruebe/)).toBeInTheDocument()
    const envio = llamadas.find((l) => l.url.includes('/solicitar/'))
    expect(JSON.parse(String(envio?.init?.body))).toEqual({
      nombre: 'Vecina Nueva',
      whatsapp: '5570000001',
      acepta_datos: true,
    })
    expect(localStorage.getItem('mdf360.solicitud.abc')).toBe('secreto')
  })

  it('al volver con su código guardado ve que ya la aprobaron', async () => {
    localStorage.setItem('mdf360.solicitud.abc', 'secreto')
    montar({
      '/solicitudes/secreto/': () => json(200, { estado: 'aprobada', grupo: 'Conexión Norte' }),
      '/enlace/abc/': info,
    })
    await waitFor(() =>
      expect(screen.getByText(/Ya eres parte de Conexión Norte/)).toBeInTheDocument(),
    )
  })

  it('si la rechazaron, lo dice con amabilidad', async () => {
    localStorage.setItem('mdf360.solicitud.abc', 'secreto')
    montar({
      '/solicitudes/secreto/': () => json(200, { estado: 'rechazada', grupo: 'Conexión Norte' }),
      '/enlace/abc/': info,
    })
    expect(await screen.findByText(/no fue aprobada/)).toBeInTheDocument()
  })
})

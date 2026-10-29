import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MisDatosCard } from './mis-datos-card'

const setUser = vi.fn()
vi.mock('./use-auth', () => ({
  useAuth: () => ({ user: { id: 1, nombre: 'Ana Lopes' }, setUser }),
}))

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const perfil = {
  nombre: 'Ana',
  apellido_paterno: 'Lopes',
  apellido_materno: '',
  fecha_nacimiento: null,
  telefono_fijo: '',
  calle_numero: '',
  colonia: 'Roma',
  codigo_postal: '',
  alcaldia: '',
  devocional_personal: '',
  oracion_familias: false,
  oracion_familias_detalle: '',
  nombre_completo: 'Ana Lopes',
  tiene_foto: false,
  acepto_foto: false,
}

function montar(llamadas: { url: string; init?: RequestInit }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method && init.method !== 'GET') {
        llamadas.push({ url, init })
        return json(200, { ...perfil, apellido_paterno: 'López', nombre_completo: 'Ana López' })
      }
      return json(200, perfil)
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MisDatosCard />
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => {
  vi.unstubAllGlobals()
  setUser.mockClear()
})

describe('MisDatosCard', () => {
  it('corrige el nombre y avisa a la sesión; no ofrece datos de acceso ni de grupo', async () => {
    const llamadas = montar()
    const paterno = await screen.findByLabelText('Apellido paterno')
    fireEvent.change(paterno, { target: { value: 'López' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar mis datos' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/personas/mi-perfil/'))
    expect(llamadas[0].init?.method).toBe('PATCH')
    expect(JSON.parse(String(llamadas[0].init?.body)).apellido_paterno).toBe('López')
    await waitFor(() => expect(setUser).toHaveBeenCalledWith({ id: 1, nombre: 'Ana López' }))
    for (const prohibido of ['WhatsApp', 'Correo', 'Grupo', 'Sector', 'Líder']) {
      expect(screen.queryByLabelText(new RegExp(prohibido, 'i'))).toBeNull()
    }
  })

  it('pide aceptar el uso de la foto antes de dejar subirla', async () => {
    montar()
    const entrada = (await screen.findByText('Subir mi foto')).closest('label')!
    expect(entrada.className).toContain('opacity-50')
    fireEvent.click(screen.getByRole('checkbox', { name: /Acepto que mi fotografía/ }))
    await waitFor(() => expect(entrada.className).not.toContain('opacity-50'))
  })
})

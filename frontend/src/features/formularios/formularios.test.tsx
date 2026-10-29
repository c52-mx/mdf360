import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DatosAdicionalesCard } from './datos-adicionales-card'
import { DisenadorPage } from './disenador-page'
import type { CampoExtra } from './types'

vi.mock('@/features/auth/use-auth', () => ({ useCan: () => true }))

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const campo = (c: Partial<CampoExtra> & Pick<CampoExtra, 'clave' | 'etiqueta' | 'tipo'>): CampoExtra => ({
  ayuda: '',
  requerido: false,
  activo: true,
  reportable: false,
  opciones: [],
  objetivo: '',
  ...c,
})

const catalogo = {
  entidades: [],
  tipos: [
    { clave: 'texto', nombre: 'Texto corto' },
    { clave: 'numero', nombre: 'Número' },
    { clave: 'seleccion', nombre: 'Lista de opciones' },
    { clave: 'relacion', nombre: 'Relación con otro registro' },
  ],
  objetivos: [{ clave: 'persona', nombre: 'Persona' }],
}

function montar(campos: CampoExtra[], llamadas: { url: string; init?: RequestInit }[] = [], ui = <DisenadorPage />) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method && init.method !== 'GET') {
        llamadas.push({ url, init })
        return json(200, { entidad: 'persona', version: 2, campos })
      }
      if (url.endsWith('/api/formularios/')) return json(200, catalogo)
      if (url.includes('/reporte/')) return json(200, [])
      return json(200, { entidad: 'persona', version: 1, campos })
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={['/formularios/persona']}>
        <Routes>
          <Route path="/formularios/:entidad" element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => vi.unstubAllGlobals())

describe('Diseñador de formularios', () => {
  it('agrega un campo nuevo y lo guarda como versión nueva', async () => {
    const llamadas = montar([campo({ clave: 'talla', etiqueta: 'Talla', tipo: 'texto' })])
    await screen.findByText(/Versión 1/)
    fireEvent.click(screen.getByRole('button', { name: 'Agregar campo' }))
    const etiquetas = screen.getAllByLabelText('Etiqueta (lo que ve quien captura)')
    fireEvent.change(etiquetas[1], { target: { value: 'Apodo' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar formulario' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/formularios/persona/'))
    const campos = JSON.parse(String(llamadas[0].init?.body)).campos
    expect(campos).toHaveLength(2)
    expect(campos[1]).toMatchObject({ etiqueta: 'Apodo', tipo: 'texto', activo: true })
    expect(llamadas[0].init?.method).toBe('PUT')
  })

  it('no deja cambiar el tipo de un campo que ya existe y permite desactivarlo', async () => {
    const llamadas = montar([campo({ clave: 'talla', etiqueta: 'Talla', tipo: 'texto' })])
    const tipo = await screen.findByLabelText('Tipo de campo')
    expect(tipo).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Activo'))
    fireEvent.click(screen.getByRole('button', { name: 'Guardar formulario' }))
    await waitFor(() => expect(llamadas.length).toBe(1))
    expect(JSON.parse(String(llamadas[0].init?.body)).campos[0].activo).toBe(false)
  })
})

describe('Datos adicionales', () => {
  it('muestra solo los campos activos, guarda las respuestas y no aparece sin campos', async () => {
    const campos = [
      campo({ clave: 'talla', etiqueta: 'Talla', tipo: 'seleccion', opciones: ['S', 'M'] }),
      campo({ clave: 'viejo', etiqueta: 'Campo viejo', tipo: 'texto', activo: false }),
    ]
    const llamadas = montar(
      campos,
      [],
      <DatosAdicionalesCard entidad="persona" id={5} datos={{ talla: 'S' }} puedeEditar refrescar={['persona', '5']} />,
    )
    const talla = await screen.findByLabelText('Talla')
    expect(screen.queryByText('Campo viejo')).toBeNull()
    fireEvent.change(talla, { target: { value: 'M' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar datos adicionales' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/personas/5/'))
    expect(JSON.parse(String(llamadas[0].init?.body))).toEqual({ datos_extra: { talla: 'M' } })
  })
})

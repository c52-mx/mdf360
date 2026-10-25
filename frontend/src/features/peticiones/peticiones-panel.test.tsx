import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PeticionesPanel } from './peticiones-panel'

const formulario = {
  version: 1,
  campos: [
    { clave: 'peticion', etiqueta: 'Petición', tipo: 'textarea', requerido: true, activo: true, opciones: [] },
    { clave: 'solicitante', etiqueta: 'Quién la pide', tipo: 'texto', requerido: false, activo: true, opciones: [] },
    { clave: 'viejo', etiqueta: 'Campo desactivado', tipo: 'texto', requerido: false, activo: false, opciones: [] },
  ],
}

const peticion = {
  id: 1,
  origen: {
    tipo: 'grupo',
    tipo_display: 'Grupo de Conexión',
    id: 3,
    etiqueta: 'Grupo de Conexión · Conexión Norte · reunión del 22/10/2026',
    referencia_id: 5,
  },
  estado: 'activa',
  estado_display: 'Activa',
  creada_en: '2026-10-22T20:00:00Z',
  expira_en: '2026-11-21T20:00:00Z',
  datos: { peticion: 'Por la salud de mi mamá', solicitante: 'María' },
  formulario_version: 1,
}

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

function montar(puedeRegistrar: boolean) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <PeticionesPanel origenTipo="grupo" origenId={3} referenciaId={5} puedeRegistrar={puedeRegistrar} />
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('PeticionesPanel', () => {
  it('muestra cada petición con su origen y las etiquetas del formulario', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        url.includes('/formulario/')
          ? json(200, formulario)
          : json(200, { count: 1, next: null, previous: null, results: [peticion] }),
      ),
    )
    montar(false)
    expect(await screen.findByText(/Conexión Norte · reunión del 22\/10\/2026/)).toBeInTheDocument()
    expect(screen.getByText('Por la salud de mi mamá')).toBeInTheDocument()
    expect(screen.getByText('Quién la pide')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Guardar petición' })).toBeNull()
  })

  it('no aparece si la persona no puede ver ni capturar', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        url.includes('/formulario/')
          ? json(200, formulario)
          : json(200, { count: 0, next: null, previous: null, results: [] }),
      ),
    )
    montar(false)
    await waitFor(() => expect(document.body.textContent).not.toContain('Peticiones de oración'))
  })

  it('registra con el origen y la reunión, y solo muestra los campos activos', async () => {
    const post = vi.fn((body: Record<string, unknown>) => json(201, { ...peticion, recibido: body }))
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (init?.method === 'POST') return post(JSON.parse(String(init.body)) as Record<string, unknown>)
        if (url.includes('/formulario/')) return json(200, formulario)
        return json(200, { count: 0, next: null, previous: null, results: [] })
      }),
    )
    montar(true)
    fireEvent.change(await screen.findByLabelText('Petición'), { target: { value: 'Por mi trabajo' } })
    expect(screen.queryByLabelText('Campo desactivado')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Guardar petición' }))
    expect(await screen.findByText('Petición registrada.')).toBeInTheDocument()
    expect(post).toHaveBeenCalledTimes(1)
    expect(post.mock.calls[0][0]).toEqual({
      origen_tipo: 'grupo',
      origen_id: 3,
      referencia_id: 5,
      datos: { peticion: 'Por mi trabajo' },
    })
  })
})

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
  visibilidad: 'grupo',
  visibilidad_display: 'Mi grupo',
  ocultar_nombre: false,
  puede_gestionar: true,
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
      visibilidad: 'lideres',
      ocultar_nombre: false,
    })
  })

  it('permite elegir el alcance y ocultar el nombre; lo envía al registrar', async () => {
    const post = vi.fn((body: Record<string, unknown>) => json(201, { ...peticion, recibido: body }))
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
        if (init?.method === 'POST') return post(JSON.parse(String(init.body)) as Record<string, unknown>)
        if (url.includes('/formulario/')) return json(200, { ...formulario, visibilidad_por_defecto: 'grupo', dias_retencion: 30 })
        return json(200, { count: 0, next: null, previous: null, results: [] })
      }),
    )
    montar(true)
    const alcance = await screen.findByLabelText('¿Quién puede verla?')
    expect(alcance).toHaveValue('grupo') // el valor por defecto viene de la configuración
    expect(screen.getByLabelText(/Ocultar el nombre/)).toBeInTheDocument()
    // Leyenda de privacidad siempre visible, según el alcance y los días de conservación
    expect(screen.getByText(/de acuerdo en que la lea todos los integrantes del grupo/)).toBeInTheDocument()
    expect(screen.getByText(/se borra sola a los 30 días/)).toBeInTheDocument()
    fireEvent.change(alcance, { target: { value: 'equipo' } })
    expect(screen.getByText(/de acuerdo en que la lea todos los integrantes del grupo, el equipo de oración/)).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText(/Ocultar el nombre/))
    fireEvent.change(screen.getByLabelText('Petición'), { target: { value: 'Por mi familia' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar petición' }))
    await waitFor(() => expect(post).toHaveBeenCalledTimes(1))
    expect(post.mock.calls[0][0]).toMatchObject({ visibilidad: 'equipo', ocultar_nombre: true })
    fireEvent.change(alcance, { target: { value: 'lideres' } })
    expect(screen.queryByLabelText(/Ocultar el nombre/)).toBeNull() // no aplica si es solo líderes
  })

  it('muestra el alcance de cada petición y solo da el botón de atender a quien puede gestionarla', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) =>
        url.includes('/formulario/')
          ? json(200, formulario)
          : json(200, {
              count: 2,
              next: null,
              previous: null,
              results: [
                { ...peticion, id: 1 },
                { ...peticion, id: 2, puede_gestionar: false, visibilidad_display: 'Equipo de oración', ocultar_nombre: true },
              ],
            }),
      ),
    )
    montar(false)
    expect(await screen.findByText('Mi grupo')).toBeInTheDocument()
    expect(screen.getByText('Equipo de oración')).toBeInTheDocument()
    expect(screen.getByText(/nombre de quien la pide está oculto/)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Marcar como atendida' })).toHaveLength(1)
  })
})

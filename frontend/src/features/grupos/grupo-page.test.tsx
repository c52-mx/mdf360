import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider } from '@/design-system'
import { GrupoPage } from './grupo-page'
import type { GrupoDetalle } from './types'

vi.mock('@/features/tablero/tablero-panel', () => ({ TableroPanel: () => null }))
vi.mock('@/features/peticiones/peticiones-panel', () => ({ PeticionesPanel: () => null }))

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

const grupo: GrupoDetalle = {
  id: 4,
  nombre: 'Conexión Norte',
  tipo: 'conexion',
  sector: 'K',
  casa: 6,
  ubicacion: 'Sector K, Casa 6',
  suspendido: false,
  suspension_motivo: '',
  suspendido_en: null,
  colonia: 'Centro',
  dia_semana: 3,
  dia: 'Jueves',
  hora: '19:00',
  lideres: ['Laura'],
  integrantes: 2,
  mis_roles: [],
  ofrendas_con_diferencia: null,
  miembros: [
    { id: 11, persona_id: 1, nombre: 'Beto Bueno', rol: 'asistente', rol_display: 'Asistente', invitado: false },
  ],
  reuniones: [
    {
      id: 9,
      fecha: '2026-10-22',
      presentes: 5,
      registrados: 8,
      notas: 'Se oró por la familia Pérez',
      peticiones: 2,
      ofrendas: { cantidad: 1, total: '350.00' },
    },
  ],
  puede_capturar: true,
  puede_gestionar: true,
  puede_administrar: true,
  puede_publicar: true,
  enlace: null,
  datos_extra: {},
  datos_extra_etiquetas: {},
}

const rol = (clave: string, nombre: string, de_gestion = false) => ({
  ambito: 'grupo', clave, nombre, descripcion: '', permisos: [], activo: true, es_base: true, en_uso: 0, de_gestion,
})
const rolesGrupo = [
  rol('asistente', 'Asistente'),
  rol('anfitrion', 'Anfitrión'),
  rol('lider', 'Líder', true),
  rol('supervisor', 'Supervisor', true),
]

function montar(datos = grupo, llamadas: { url: string; init?: RequestInit }[] = []) {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      if (init?.method && init.method !== 'GET') {
        llamadas.push({ url, init })
        return json(200, datos)
      }
      if (url.includes('/roles-equipo/')) return json(200, rolesGrupo)
      if (url.includes('/api/formularios/')) return json(200, { entidad: 'grupo', version: 0, campos: [] })
      if (url.includes('/solicitudes/')) return json(200, [])
      return json(200, datos)
    }),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/grupos/4']}>
          <Routes>
            <Route path="/grupos/:id" element={<GrupoPage />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
  return llamadas
}

afterEach(() => vi.unstubAllGlobals())

describe('GrupoPage', () => {
  it('muestra sector y casa y, al abrir el historial, lo que ocurrió en cada reunión', async () => {
    montar()
    expect((await screen.findAllByText(/Sector K, Casa 6/)).length).toBeGreaterThan(0)
    // El historial arranca cerrado: nada de reuniones hasta consultarlo
    expect(screen.queryByText('5 de 8 presentes')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /Historial de reuniones/ }))
    expect(screen.getByText('Observaciones: Se oró por la familia Pérez')).toBeInTheDocument()
    expect(screen.getByText('2 peticiones')).toBeInTheDocument()
    expect(screen.getByText(/Ofrendas: \$350\.00/)).toBeInTheDocument()
    expect(screen.getByText('5 de 8 presentes')).toBeInTheDocument()
  })

  it('pone primero el tablero y al final la zona de riesgo', async () => {
    montar()
    await screen.findByRole('heading', { name: 'Integrantes' })
    const zona = screen.getByRole('region', { name: 'Zona de riesgo' })
    const integrantes = screen.getByRole('heading', { name: 'Integrantes' })
    expect(integrantes.compareDocumentPosition(zona) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Sumar gente' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Invitar por enlace o QR' })).toBeInTheDocument()
  })

  it('la reunión pide día y hora: no se guarda sin ellos', async () => {
    montar({ ...grupo, dia_semana: null, dia: '', hora: '' })
    expect(await screen.findByText(/Falta el día o la hora de la reunión/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Editar datos' }))
    expect(screen.getByRole('button', { name: 'Guardar' })).toBeDisabled()
  })

  it('cambia el rol de un integrante', async () => {
    const llamadas = montar()
    fireEvent.change(await screen.findByLabelText('Rol de Beto Bueno'), { target: { value: 'anfitrion' } })
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/grupos/4/integrantes/11/'))
    expect(llamadas[0].init?.method).toBe('PATCH')
    expect(JSON.parse(String(llamadas[0].init?.body))).toEqual({ rol: 'anfitrion' })
  })

  it('suspende el grupo con su motivo después de confirmar', async () => {
    const llamadas = montar()
    const boton = await screen.findByRole('button', { name: 'Suspender grupo' })
    expect(boton).toBeDisabled() // sin motivo no se puede
    fireEvent.change(screen.getByLabelText('Motivo de la suspensión'), {
      target: { value: 'El anfitrión se mudó' },
    })
    fireEvent.click(boton)
    fireEvent.click(screen.getByRole('button', { name: 'Sí, suspender' }))
    await waitFor(() => expect(llamadas.map((l) => l.url)).toContain('/api/grupos/4/suspender/'))
    expect(JSON.parse(String(llamadas[0].init?.body))).toEqual({ motivo: 'El anfitrión se mudó' })
  })

  it('un grupo suspendido muestra el motivo, no deja pasar lista y ofrece reactivar', async () => {
    montar({
      ...grupo,
      suspendido: true,
      suspension_motivo: 'Vacaciones largas',
      suspendido_en: '2026-10-20',
    })
    expect(await screen.findByText(/Motivo: Vacaciones largas/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Pasar lista de hoy' })).toBeNull()
    expect(screen.getByRole('button', { name: 'Reactivar grupo' })).toBeInTheDocument()
  })
})

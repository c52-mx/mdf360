import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { pendientes, sincronizar, type Pendiente } from './outbox'

const base: Omit<Pendiente, 'id'> = {
  usuarioId: 1,
  grupoId: 3,
  grupoNombre: 'Conexión Norte',
  fecha: '2026-10-22',
  asistencias: [{ persona_id: 10, presente: true }],
  notas: '',
  capturadoEn: '2026-10-22T21:00:00.000Z',
}

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status }))

type Llamada = { url: string; metodo: string; cuerpo?: Record<string, unknown> }

function simular(respuesta: (l: Llamada) => Promise<Response>) {
  const llamadas: Llamada[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes('/csrf/')) return json(200, { csrfToken: 'x' })
      const l = {
        url,
        metodo: init?.method ?? 'GET',
        cuerpo: init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined,
      }
      llamadas.push(l)
      return respuesta(l)
    }),
  )
  return llamadas
}

beforeEach(() => localStorage.clear())
afterEach(() => vi.unstubAllGlobals())

describe('cola de capturas sin conexión', () => {
  it('guarda, lista por usuario y quita', () => {
    const a = pendientes.agregar(base)
    pendientes.agregar({ ...base, usuarioId: 2, grupoId: 9 })
    expect(pendientes.listar(1)).toHaveLength(1)
    expect(pendientes.listar()).toHaveLength(2)
    pendientes.quitar(a.id)
    expect(pendientes.listar(1)).toHaveLength(0)
  })

  it('una nueva captura del mismo grupo y día reemplaza a la anterior', () => {
    pendientes.agregar(base)
    pendientes.agregar({ ...base, asistencias: [{ persona_id: 10, presente: false }] })
    const lista = pendientes.listar(1)
    expect(lista).toHaveLength(1)
    expect(lista[0].asistencias[0].presente).toBe(false)
  })

  it('avisa a los suscriptores cuando cambia', () => {
    const aviso = vi.fn()
    const baja = pendientes.suscribir(aviso)
    pendientes.agregar(base)
    expect(aviso).toHaveBeenCalled()
    baja()
  })
})

describe('sincronizar', () => {
  it('abre la reunión con el momento de captura y envía la lista', async () => {
    pendientes.agregar(base)
    const llamadas = simular((l) =>
      l.metodo === 'POST' ? json(201, { id: 77, fecha: base.fecha }) : json(200, { presentes: 1, omitidos: 0 }),
    )
    const r = await sincronizar(1)
    expect(r).toEqual({ enviados: 1, fallidos: 0, sinConexion: false })
    expect(llamadas[0]).toMatchObject({ url: '/api/grupos/3/reuniones/', metodo: 'POST' })
    expect(llamadas[0].cuerpo).toEqual({ fecha: '2026-10-22', capturado_en: base.capturadoEn })
    expect(llamadas[1]).toMatchObject({ url: '/api/grupos/reuniones/77/', metodo: 'PUT' })
    expect(llamadas[1].cuerpo?.capturado_en).toBe(base.capturadoEn)
    expect(pendientes.listar(1)).toHaveLength(0)
  })

  it('con reunión ya existente solo envía la lista', async () => {
    pendientes.agregar({ ...base, reunionId: 5 })
    const llamadas = simular(() => json(200, { presentes: 1, omitidos: 0 }))
    await sincronizar(1)
    expect(llamadas).toHaveLength(1)
    expect(llamadas[0].url).toBe('/api/grupos/reuniones/5/')
  })

  it('si falta la conexión se detiene y conserva la captura', async () => {
    pendientes.agregar(base)
    simular(() => Promise.reject(new TypeError('Failed to fetch')))
    const r = await sincronizar(1)
    expect(r.sinConexion).toBe(true)
    expect(pendientes.listar(1)).toHaveLength(1)
    expect(pendientes.listar(1)[0].error).toBeUndefined()
  })

  it('un rechazo definitivo se marca con su motivo y no se reintenta', async () => {
    pendientes.agregar(base)
    simular(() => json(400, { code: 'too_old', detail: 'La captura es demasiado antigua.' }))
    const r = await sincronizar(1)
    expect(r).toEqual({ enviados: 0, fallidos: 1, sinConexion: false })
    expect(pendientes.listar(1)[0].error).toBe('La captura es demasiado antigua.')
    const llamadas = simular(() => json(200, {}))
    await sincronizar(1)
    expect(llamadas).toHaveLength(0)
  })

  it('un error del servidor (5xx) se trata como temporal', async () => {
    pendientes.agregar({ ...base, reunionId: 5 })
    simular(() => json(503, { detail: 'No disponible' }))
    const r = await sincronizar(1)
    expect(r.sinConexion).toBe(true)
    expect(pendientes.listar(1)[0].error).toBeUndefined()
  })

  it('no envía las capturas de otro usuario', async () => {
    pendientes.agregar({ ...base, usuarioId: 2, reunionId: 5 })
    const llamadas = simular(() => json(200, {}))
    await sincronizar(1)
    expect(llamadas).toHaveLength(0)
    expect(pendientes.listar(2)).toHaveLength(1)
  })

  it('si el primer envío se confirma y el segundo falla, no repite la reunión abierta', async () => {
    pendientes.agregar(base)
    let intento = 0
    const llamadas = simular((l) => {
      if (l.metodo === 'POST') return json(201, { id: 77, fecha: base.fecha })
      intento += 1
      return intento === 1 ? Promise.reject(new TypeError('sin red')) : json(200, { presentes: 1, omitidos: 0 })
    })
    await sincronizar(1)
    expect(pendientes.listar(1)[0].reunionId).toBe(77)
    await sincronizar(1)
    expect(llamadas.filter((l) => l.metodo === 'POST')).toHaveLength(1)
    expect(pendientes.listar(1)).toHaveLength(0)
  })
})

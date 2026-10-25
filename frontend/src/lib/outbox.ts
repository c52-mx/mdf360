/**
 * Cola de capturas hechas sin conexión (NF-06).
 *
 * Las listas de asistencia se guardan en el teléfono (son pocos KB) y se envían cuando vuelve la
 * señal. Cada captura lleva el momento real en que se hizo: el servidor lo usa para respetar la
 * regla «el Secretario solo captura el mismo día» y para no pisar cambios más recientes.
 */
import { api, ApiError } from './api'

export interface Pendiente {
  id: string
  usuarioId: number
  grupoId: number
  grupoNombre: string
  fecha: string // día de la reunión (AAAA-MM-DD)
  reunionId?: number
  asistencias: { persona_id: number; presente: boolean }[]
  notas: string
  capturadoEn: string // ISO
  error?: string
}

const CLAVE = 'mdf360.pendientes'
const EVENTO = 'mdf360:pendientes'

function leer(): Pendiente[] {
  try {
    return JSON.parse(localStorage.getItem(CLAVE) ?? '[]') as Pendiente[]
  } catch {
    return []
  }
}

function escribir(lista: Pendiente[]) {
  try {
    localStorage.setItem(CLAVE, JSON.stringify(lista))
  } catch {
    // sin almacenamiento disponible: no hay dónde guardar la captura
    throw new Error('No se pudo guardar la lista en este dispositivo.')
  }
  window.dispatchEvent(new Event(EVENTO))
}

/** Texto crudo de la cola: sirve de instantánea estable para useSyncExternalStore. */
export function instantanea(): string {
  try {
    return localStorage.getItem(CLAVE) ?? '[]'
  } catch {
    return '[]'
  }
}

export const pendientes = {
  listar: (usuarioId?: number) => leer().filter((p) => usuarioId === undefined || p.usuarioId === usuarioId),

  /** Si ya hay una captura pendiente para esa reunión o ese día y grupo, la reemplaza. */
  agregar(p: Omit<Pendiente, 'id'>): Pendiente {
    const nuevo = { ...p, id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}` }
    const resto = leer().filter(
      (x) =>
        !(
          x.usuarioId === p.usuarioId &&
          x.grupoId === p.grupoId &&
          (p.reunionId ? x.reunionId === p.reunionId : !x.reunionId && x.fecha === p.fecha)
        ),
    )
    escribir([...resto, nuevo])
    return nuevo
  },

  quitar: (id: string) => escribir(leer().filter((p) => p.id !== id)),

  actualizar(id: string, cambios: Partial<Pendiente>) {
    escribir(leer().map((p) => (p.id === id ? { ...p, ...cambios } : p)))
  },

  suscribir(fn: () => void) {
    window.addEventListener(EVENTO, fn)
    window.addEventListener('storage', fn)
    return () => {
      window.removeEventListener(EVENTO, fn)
      window.removeEventListener('storage', fn)
    }
  },
}

/** Fallo de red (sin conexión o servidor inalcanzable), distinto de una respuesta de error. */
export const esErrorDeRed = (e: unknown) => e instanceof TypeError

export interface ResultadoSync {
  enviados: number
  fallidos: number
  sinConexion: boolean
}

let sincronizando = false

/** Envía en orden las capturas del usuario. Se detiene si vuelve a faltar la conexión. */
export async function sincronizar(usuarioId: number): Promise<ResultadoSync> {
  const resultado: ResultadoSync = { enviados: 0, fallidos: 0, sinConexion: false }
  if (sincronizando) return resultado
  sincronizando = true
  try {
    for (const p of pendientes.listar(usuarioId).filter((x) => !x.error)) {
      try {
        let reunionId = p.reunionId
        if (!reunionId) {
          const abierta = await api<{ id: number }>(`/api/grupos/${p.grupoId}/reuniones/`, {
            method: 'POST',
            body: { fecha: p.fecha, capturado_en: p.capturadoEn },
          })
          reunionId = abierta.id
          pendientes.actualizar(p.id, { reunionId })
        }
        await api(`/api/grupos/reuniones/${reunionId}/`, {
          method: 'PUT',
          body: { asistencias: p.asistencias, notas: p.notas, capturado_en: p.capturadoEn },
        })
        pendientes.quitar(p.id)
        resultado.enviados += 1
      } catch (e) {
        if (esErrorDeRed(e) || (e instanceof ApiError && e.status >= 500)) {
          resultado.sinConexion = true
          break
        }
        // Rechazo definitivo (permiso, captura muy antigua…): se marca para no reintentar en bucle
        pendientes.actualizar(p.id, { error: e instanceof Error ? e.message : 'No se pudo enviar.' })
        resultado.fallidos += 1
      }
    }
  } finally {
    sincronizando = false
  }
  return resultado
}

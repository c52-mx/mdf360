/**
 * Los tres espacios de MDF360 (enfoque del 9-nov-2026):
 * - Comunidad: lo que se publica y lo que me toca a mí (muro, avisos, orar, mi perfil).
 * - Grupos: mis grupos de conexión y ministerios, y las tareas de quien sirve en ellos.
 * - Administración: las herramientas de quien administra algo (personas, roles, configuración…).
 * Quien no administra nada solo ve Comunidad y Grupos; los roles administrativos ven los tres.
 */
export type Espacio = 'comunidad' | 'grupos' | 'admin'

export const ESPACIOS: Record<Espacio, { etiqueta: string; inicio: string }> = {
  comunidad: { etiqueta: 'Comunidad', inicio: '/' },
  grupos: { etiqueta: 'Grupos', inicio: '/grupos' },
  admin: { etiqueta: 'Administración', inicio: '/personas' },
}

/** Con alguno de estos permisos la persona administra algo y ve el espacio Administración. */
export const PERMISOS_ADMIN = [
  'personas.ver',
  'personas.editar',
  'personas.baja',
  'roles.gestionar',
  'roles.administrar',
  'unidades.gestionar',
  'avisos.iglesia',
  'avisos.personas',
  'bitacora.ver',
  'grupos.gestionar',
  'ofrendas.ver_todas',
  'ofrendas.iglesia_capturar',
  'ofrendas.iglesia_avalar',
  'ofrendas.catalogo',
  'config.gestionar',
  'formularios.gestionar',
  'peticiones.configurar',
]

/** Supervisor y Líder solo traen «invitar» y «registrar contactos»: es su servicio, no administración. */
export function espaciosDe(permisos: readonly string[] | undefined): Espacio[] {
  const tiene = new Set(permisos ?? [])
  const administra = PERMISOS_ADMIN.some((p) => tiene.has(p))
  return administra ? ['comunidad', 'grupos', 'admin'] : ['comunidad', 'grupos']
}

/** Rutas que solo existen en Administración. */
const RUTAS_ADMIN = [
  '/personas',
  '/roles',
  '/permisos',
  '/formularios',
  '/bitacora',
  '/configuracion',
  '/aviso-privacidad',
  '/diseno',
]
/** Rutas de uso mixto: son de Administración si la persona la tiene; si no, viven en Grupos. */
const RUTAS_MIXTAS = ['/personas/nueva', '/invitar', '/ofrendas']
const RUTAS_GRUPOS = ['/grupos', '/ministerios', '/peticiones', '/estudios']
const RUTAS_COMUNIDAD_EN_PETICIONES = '/peticiones/formulario'

function coincide(pathname: string, base: string): boolean {
  return pathname === base || pathname.startsWith(`${base}/`)
}

/** En qué espacio cae una ruta para esta persona (según los espacios que tiene). */
export function espacioDeRuta(pathname: string, espacios: readonly Espacio[]): Espacio {
  if (RUTAS_MIXTAS.some((r) => coincide(pathname, r))) {
    return espacios.includes('admin') ? 'admin' : 'grupos'
  }
  if (RUTAS_ADMIN.some((r) => coincide(pathname, r))) return 'admin'
  if (pathname === RUTAS_COMUNIDAD_EN_PETICIONES) return 'comunidad'
  if (RUTAS_GRUPOS.some((r) => coincide(pathname, r))) return 'grupos'
  return 'comunidad'
}

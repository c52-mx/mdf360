export type Nivel = 'contacto' | 'participante' | 'edu'
export type Procedencia = 'miembro' | 'invitado_grupo' | 'visitante' | 'externo'

export const nivelLabel: Record<Nivel, string> = {
  contacto: 'Contacto',
  participante: 'Participante',
  edu: 'Expediente completo',
}

/** Qué significa cada nivel de registro, para quien captura. */
export const nivelAyuda: Record<Nivel, string> = {
  contacto: 'Alguien que dejó su número o vino invitado. Solo tenemos lo básico para localizarlo.',
  participante: 'Ya asiste y está en seguimiento. Se le registran sus procesos de discipulado.',
  edu: 'Expediente digital completo (EDU): tiene todos los datos de la Radiografía de miembros.',
}

export const procedenciaOptions: { value: Procedencia; label: string }[] = [
  { value: 'miembro', label: 'Miembro de la iglesia' },
  { value: 'invitado_grupo', label: 'Invitado de grupo' },
  { value: 'visitante', label: 'Visitante' },
  { value: 'externo', label: 'Externo' },
]

export interface PersonaResumen {
  id: number
  nombre_completo: string
  nivel: Nivel
  procedencia: Procedencia
  whatsapp: string
  grupo_conexion: string
  activo: boolean
  tiene_foto: boolean
  roles: string[]
  grupos: string[]
}

export interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface ProcesoFila {
  proceso: number
  nombre: string
  pide_maestro: boolean
  completado: boolean
  fecha: string | null
  maestro: string
}

export interface Persona {
  id: number
  roles: string[]
  grupos: string[]
  nivel: Nivel
  procedencia: Procedencia
  activo: boolean
  nombre: string
  apellido_paterno: string
  apellido_materno: string
  nombre_completo: string
  fecha_nacimiento: string | null
  edad: number | null
  tiene_foto: boolean
  whatsapp: string
  telefono_fijo: string
  email: string
  calle_numero: string
  colonia: string
  codigo_postal: string
  alcaldia: string
  sector: string
  grupo_conexion: string
  lider: string
  miembro_desde: string | null
  sirve_en_ministerio: boolean
  ministerios: string
  devocional_personal: string
  oracion_familias: boolean
  oracion_familias_detalle: string
  otros_cursos: string
  observaciones: string
  faltantes_edu: string[]
  procesos: ProcesoFila[]
  vehiculos: { id: number; descripcion: string; color: string; placas: string }[]
  actualizado_en: string
}

export interface Movimiento {
  id: number
  tipo: string
  tipo_display: string
  fecha: string
  motivo: string
  iglesia_destino: string
}

export const fotoUrl = (p: { id: number; tiene_foto: boolean }, version = '') =>
  p.tiene_foto ? `/api/personas/${p.id}/foto/${version ? `?v=${encodeURIComponent(version)}` : ''}` : undefined

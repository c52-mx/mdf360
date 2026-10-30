export const dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

export interface GrupoResumen {
  id: number
  nombre: string
  tipo: 'conexion' | 'lideres'
  sector: string
  casa: number | null
  ubicacion: string
  suspendido: boolean
  suspension_motivo: string
  suspendido_en: string | null
  colonia: string
  dia_semana: number | null
  dia: string
  hora: string
  lideres: string[]
  integrantes: number
  mis_roles: string[]
  ofrendas_con_diferencia: number | null
}

export interface Miembro {
  id: number
  persona_id: number
  nombre: string
  rol: string
  rol_display: string
  invitado: boolean
}

export interface ReunionDelGrupo {
  id: number
  fecha: string
  presentes?: number
  registrados?: number
  notas?: string
  peticiones?: number
  /** null si la persona no puede ver las finanzas del grupo. */
  ofrendas?: { cantidad: number; total: string } | null
}

export const SECTORES = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')

export interface GrupoDetalle extends GrupoResumen {
  miembros: Miembro[]
  reuniones: ReunionDelGrupo[]
  puede_capturar: boolean
  puede_gestionar: boolean
  puede_administrar: boolean
  puede_publicar: boolean
  datos_extra: Record<string, string | number | boolean | null>
  datos_extra_etiquetas: Record<string, string>
  /** Ruta del enlace de ingreso (solo para quien gestiona el grupo). */
  enlace: string | null
}

export interface Estudio {
  id: number
  semana: string
  titulo: string
  pdf_adultos: string | null
  pdf_ninos: string | null
  audio: string | null
}

export interface FilaAsistencia {
  persona_id: number
  nombre: string
  roles: string[]
  invitado: boolean
  presente: boolean
  registrada: boolean
}

export interface ReunionDetalle {
  id: number
  fecha: string
  notas: string
  grupo: { id: number; nombre: string }
  personas: FilaAsistencia[]
  estudio: Estudio | null
  puede_modificar: boolean
}

export const fechaLarga = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('es-MX', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

export const dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

export interface GrupoResumen {
  id: number
  nombre: string
  tipo: 'conexion' | 'lideres'
  sector: string
  colonia: string
  dia_semana: number | null
  dia: string
  hora: string
  lideres: string[]
  integrantes: number
  mis_roles: string[]
}

export interface Miembro {
  id: number
  persona_id: number
  nombre: string
  rol: string
  rol_display: string
  invitado: boolean
}

export interface GrupoDetalle extends GrupoResumen {
  miembros: Miembro[]
  reuniones: { id: number; fecha: string; presentes?: number; registrados?: number }[]
  puede_capturar: boolean
  puede_gestionar: boolean
  puede_administrar: boolean
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

export const rolesGrupo = [
  { value: 'asistente', label: 'Asistente' },
  { value: 'anfitrion', label: 'Anfitrión' },
  { value: 'secretario', label: 'Secretario' },
  { value: 'tesorero', label: 'Tesorero' },
  { value: 'lider', label: 'Líder' },
  { value: 'supervisor', label: 'Supervisor' },
]

export const fechaLarga = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('es-MX', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

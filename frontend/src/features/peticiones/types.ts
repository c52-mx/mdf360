export type TipoCampo = 'texto' | 'textarea' | 'seleccion' | 'casilla'

export interface Campo {
  clave: string
  etiqueta: string
  tipo: TipoCampo
  requerido: boolean
  activo: boolean
  /** Si el campo identifica a la persona; se oculta cuando se pide ocultar el nombre. */
  identifica?: boolean
  opciones: string[]
}

export type Visibilidad = 'lideres' | 'grupo' | 'equipo'

export const visibilidadOpciones: { value: Visibilidad; label: string; ayuda: string }[] = [
  { value: 'lideres', label: 'Solo líderes', ayuda: 'La ven el Líder, el Supervisor y la dirección.' },
  { value: 'grupo', label: 'Mi grupo', ayuda: 'La ven todos los integrantes del grupo.' },
  {
    value: 'equipo',
    label: 'Equipo de oración',
    ayuda: 'La ve el grupo y el equipo de oración de la iglesia.',
  },
]

export interface Formulario {
  version: number
  campos: Campo[]
  visibilidad_por_defecto?: Visibilidad
}

export interface Origen {
  tipo: string
  tipo_display: string
  id: number
  etiqueta: string
  referencia_id: number | null
}

export type Valores = Record<string, string | boolean>

export interface Peticion {
  id: number
  origen: Origen
  estado: 'activa' | 'atendida'
  estado_display: string
  visibilidad: Visibilidad
  visibilidad_display: string
  ocultar_nombre: boolean
  puede_gestionar?: boolean
  creada_en: string
  expira_en: string
  datos?: Valores
  formulario_version?: number
  ilegible?: boolean
}

export interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export const tipoCampoLabel: Record<TipoCampo, string> = {
  texto: 'Texto corto',
  textarea: 'Texto largo',
  seleccion: 'Lista de opciones',
  casilla: 'Casilla (sí/no)',
}

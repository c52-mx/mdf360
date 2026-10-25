export type TipoCampo = 'texto' | 'textarea' | 'seleccion' | 'casilla'

export interface Campo {
  clave: string
  etiqueta: string
  tipo: TipoCampo
  requerido: boolean
  activo: boolean
  opciones: string[]
}

export interface Formulario {
  version: number
  campos: Campo[]
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

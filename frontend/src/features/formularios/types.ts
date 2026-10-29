export type TipoCampo = 'texto' | 'textarea' | 'numero' | 'fecha' | 'seleccion' | 'casilla' | 'relacion'
export type Objetivo = 'persona' | 'grupo' | 'ministerio'
export type Entidad = 'persona' | 'grupo'

export interface CampoExtra {
  clave: string
  etiqueta: string
  tipo: TipoCampo
  ayuda: string
  requerido: boolean
  activo: boolean
  reportable: boolean
  opciones: string[]
  objetivo: Objetivo | ''
}

export interface FormularioExtra {
  entidad: Entidad
  version: number
  campos: CampoExtra[]
}

export interface CatalogoFormularios {
  entidades: { clave: Entidad; nombre: string }[]
  tipos: { clave: TipoCampo; nombre: string }[]
  objetivos: { clave: Objetivo; nombre: string }[]
}

export type Respuestas = Record<string, string | number | boolean | null | undefined>

export interface FilaReporte {
  clave: string
  etiqueta: string
  activo: boolean
  respuestas: number
  valores: { valor: string; total: number }[]
  por_grupo?: { grupo: string; total: number }[]
}

export const objetivoLabel: Record<Objetivo, string> = {
  persona: 'Persona',
  grupo: 'Grupo de Conexión',
  ministerio: 'Ministerio',
}

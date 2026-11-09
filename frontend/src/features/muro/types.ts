export type TipoReaccion = 'me_gusta' | 'amen' | 'corazon'

export interface AudienciaPublicacion {
  tipo: string
  id: number
  etiqueta: string
}

export interface Publicacion {
  id: number
  autor: string
  texto: string
  creada_en: string
  audiencias: AudienciaPublicacion[]
  es_mia: boolean
  reacciones: Partial<Record<TipoReaccion, number>>
  mi_reaccion: TipoReaccion | null
  comentarios_total: number
  fijada: boolean
  editada: boolean
  puede_editar: boolean
  puede_quitar: boolean
  puede_moderar: boolean
  /** Reportes sin atender; solo se informa a quien modera. */
  reportes: number
  yo_reporte: boolean
}

export interface PaginaMuro {
  /** Fijadas: vienen solo en la primera página. */
  fijadas: Publicacion[]
  resultados: Publicacion[]
  /** Id desde el que pedir la página siguiente; null cuando ya no hay más. */
  siguiente: number | null
}

export interface Comentario {
  id: number
  autor: string
  texto: string
  creado_en: string
  es_mio: boolean
  puede_quitar: boolean
}

export const REACCIONES: {
  tipo: TipoReaccion
  icono: string
  nombre: string
}[] = [
  { tipo: 'me_gusta', icono: '👍', nombre: 'Me gusta' },
  { tipo: 'amen', icono: '🙏', nombre: 'Amén' },
  { tipo: 'corazon', icono: '❤️', nombre: 'Me encanta' },
]

export interface Destino {
  tipo: string
  id: number
  etiqueta: string
}

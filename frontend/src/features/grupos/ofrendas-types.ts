export interface TipoOfrenda {
  id: number
  nombre: string
  para_grupo: boolean
  para_iglesia: boolean
  activo: boolean
}

export interface TiposRespuesta {
  puede_administrar: boolean
  tipos: TipoOfrenda[]
}

export interface FilaResumen {
  id: number
  origen: 'grupo' | 'iglesia'
  origen_display: string
  fecha: string
  tipo: string
  monto: string
  estado: 'pendiente' | 'avalada' | 'diferencia'
  estado_display: string
  concepto: string
}

export interface Resumen {
  filas: FilaResumen[]
  truncado: boolean
  totales: {
    total: string
    avalado: string
    por_avalar: string
    cantidad: number
    grupo: string
    iglesia: string
  }
  por_tipo: { tipo: string; monto: string }[]
  por_mes: { mes: string; grupo: string; iglesia: string }[]
}

export interface Filtros {
  desde: string
  hasta: string
  origen: string
  tipo: string
  estado: string
}

export const sinFiltros: Filtros = { desde: '', hasta: '', origen: '', tipo: '', estado: '' }

/** «2026-10» -> «oct 2026» */
export const mesCorto = (mes: string) =>
  new Date(`${mes}-01T12:00:00`).toLocaleDateString('es-MX', { month: 'short', year: 'numeric' })

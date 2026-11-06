export interface UnidadResumen {
  id: number
  nombre: string
  descripcion: string
  activa: boolean
  encargados: string[]
  integrantes: number
  mis_roles: string[]
}

export interface MiembroUnidad {
  id: number
  persona_id: number
  nombre: string
  rol: string
  rol_display: string
}

export interface UnidadDetalle extends UnidadResumen {
  miembros: MiembroUnidad[]
  puede_gestionar: boolean
  puede_administrar: boolean
  puede_ver_panel?: boolean
  /** Ruta del enlace (/servir/…) para quien gestiona al equipo; null si no hay o no puede verlo. */
  enlace?: string | null
}

export interface PanelUnidad {
  ministerio: string
  integrantes: number
  nuevos_30_dias: number
  salieron: number
  por_rol: { rol: string; rol_display: string; total: number }[]
  meses: { mes: string; sumaron: number; mensajes: number }[]
  ultimo_mensaje: string | null
  peticiones: { activas: number; atendidas: number }
}

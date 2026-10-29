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
}

export const rolesUnidad = [
  { value: 'servidor', label: 'Servidor' },
  { value: 'respaldo', label: 'Respaldo' },
  { value: 'encargado', label: 'Encargado' },
]

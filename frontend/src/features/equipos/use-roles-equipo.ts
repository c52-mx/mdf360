import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'

export type AmbitoEquipo = 'grupo' | 'ministerio'

export interface RolEquipo {
  ambito: AmbitoEquipo
  clave: string
  nombre: string
  descripcion: string
  permisos: string[]
  activo: boolean
  es_base: boolean
  en_uso: number
  /** Administra a la gente del equipo: solo la administración lo asigna. */
  de_gestion: boolean
}

/** Los roles que existen dentro de un grupo de conexión o de un ministerio. */
export function useRolesEquipo(ambito: AmbitoEquipo) {
  return useQuery({
    queryKey: ['roles-equipo', ambito],
    queryFn: () => api<RolEquipo[]>(`/api/auth/roles-equipo/?ambito=${ambito}`),
    staleTime: 60_000,
  })
}

/** Opciones para un selector: los de gestión solo si quien elige administra. */
export function opcionesDeRol(roles: RolEquipo[] | undefined, puedeAdministrar: boolean) {
  return (roles ?? [])
    .filter((r) => puedeAdministrar || !r.de_gestion)
    .map((r) => ({ value: r.clave, label: r.nombre }))
}

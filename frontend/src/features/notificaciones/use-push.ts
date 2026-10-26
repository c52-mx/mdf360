import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import {
  activarPush,
  desactivarPush,
  requiereInstalar,
  soportaPush,
  suscripcionActual,
} from '@/lib/push'

export type EstadoPush =
  | 'cargando'
  | 'no-soportado'
  | 'instalar'
  | 'apagado'
  | 'bloqueado'
  | 'inactivo'
  | 'activo'

interface ConfigPush {
  disponible: boolean
  clave_publica: string
}

/** Estado de las notificaciones en este dispositivo y acciones para activarlas o apagarlas. */
export function usePush() {
  const config = useQuery({
    queryKey: ['push-config'],
    queryFn: () => api<ConfigPush>('/api/notificaciones/config/'),
    staleTime: 5 * 60 * 1000,
  })
  const [bloqueado, setBloqueado] = useState(
    () => soportaPush() && Notification.permission === 'denied',
  )
  const [suscrito, setSuscrito] = useState<boolean | null>(null)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let vigente = true
    suscripcionActual()
      .then((s) => vigente && setSuscrito(s !== null))
      .catch(() => vigente && setSuscrito(false))
    return () => {
      vigente = false
    }
  }, [])

  let estado: EstadoPush
  if (!soportaPush()) estado = requiereInstalar() ? 'instalar' : 'no-soportado'
  else if (config.isPending || suscrito === null) estado = 'cargando'
  else if (!config.data?.disponible) estado = 'apagado'
  else if (bloqueado) estado = 'bloqueado'
  else estado = suscrito ? 'activo' : 'inactivo'

  const activar = async () => {
    if (!config.data) return
    setOcupado(true)
    setError(null)
    try {
      const resultado = await activarPush(config.data.clave_publica)
      setBloqueado(resultado === 'bloqueado')
      setSuscrito(resultado === 'activo')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo activar. Intenta de nuevo.')
    } finally {
      setOcupado(false)
    }
  }

  const desactivar = async () => {
    setOcupado(true)
    setError(null)
    try {
      await desactivarPush()
      setSuscrito(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo desactivar. Intenta de nuevo.')
    } finally {
      setOcupado(false)
    }
  }

  const probar = async () => {
    setError(null)
    try {
      await api('/api/notificaciones/probar/', { method: 'POST' })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo enviar la prueba.')
    }
  }

  return {
    estado,
    ocupado,
    error,
    activar,
    desactivar,
    probar,
  }
}

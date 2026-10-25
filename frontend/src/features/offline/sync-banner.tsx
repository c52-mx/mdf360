import { useQueryClient } from '@tanstack/react-query'
import { CloudOff, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState, useSyncExternalStore } from 'react'
import { Alert, Button } from '@/design-system'
import { useAuth } from '@/features/auth/use-auth'
import { instantanea, pendientes, sincronizar, type Pendiente } from '@/lib/outbox'

function suscribirConexion(aviso: () => void) {
  window.addEventListener('online', aviso)
  window.addEventListener('offline', aviso)
  return () => {
    window.removeEventListener('online', aviso)
    window.removeEventListener('offline', aviso)
  }
}

/** Aviso de conexión y de capturas pendientes; envía las pendientes en cuanto hay señal. */
export function SyncBanner() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const enLinea = useSyncExternalStore(suscribirConexion, () => navigator.onLine)
  const crudo = useSyncExternalStore(pendientes.suscribir, instantanea)
  const lista = useMemo(
    () => (JSON.parse(crudo) as Pendiente[]).filter((p) => p.usuarioId === user?.id),
    [crudo, user?.id],
  )
  const [enviando, setEnviando] = useState(false)
  const [aviso, setAviso] = useState('')

  const enviar = useCallback(async () => {
    if (!user || !navigator.onLine) return
    if (pendientes.listar(user.id).every((p) => p.error)) return
    setEnviando(true)
    const r = await sincronizar(user.id)
    setEnviando(false)
    if (r.enviados > 0) {
      setAviso(
        r.enviados === 1 ? 'Se envió 1 lista guardada.' : `Se enviaron ${r.enviados} listas guardadas.`,
      )
      void queryClient.invalidateQueries({ queryKey: ['grupos'] })
      void queryClient.invalidateQueries({ queryKey: ['grupo'] })
      void queryClient.invalidateQueries({ queryKey: ['reunion'] })
    }
  }, [user, queryClient])

  // Al abrir la app, al volver la señal y cada 30 s mientras haya algo pendiente
  useEffect(() => {
    const inicial = window.setTimeout(() => void enviar(), 0)
    const alVolver = () => void enviar()
    window.addEventListener('online', alVolver)
    const cada = window.setInterval(alVolver, 30_000)
    return () => {
      window.clearTimeout(inicial)
      window.removeEventListener('online', alVolver)
      window.clearInterval(cada)
    }
  }, [enviar])

  const conError = lista.filter((p) => p.error)
  const porEnviar = lista.filter((p) => !p.error)

  if (enLinea && lista.length === 0 && !aviso) return null

  return (
    <div className="mb-4 flex flex-col gap-3">
      {!enLinea ? (
        <Alert tone="warning">
          <span className="flex items-center gap-2">
            <CloudOff aria-hidden className="size-5" />
            Sin conexión. Puedes seguir pasando lista: se guarda en tu teléfono y se envía sola.
          </span>
        </Alert>
      ) : null}
      {porEnviar.length > 0 ? (
        <Alert tone="info">
          <span className="flex flex-wrap items-center justify-between gap-3">
            <span>
              {porEnviar.length === 1
                ? '1 lista guardada pendiente de enviar.'
                : `${porEnviar.length} listas guardadas pendientes de enviar.`}
            </span>
            {enLinea ? (
              <Button size="sm" variant="outline" onClick={() => void enviar()} disabled={enviando}>
                <RefreshCw aria-hidden className="size-4" />
                {enviando ? 'Enviando…' : 'Enviar ahora'}
              </Button>
            ) : null}
          </span>
        </Alert>
      ) : null}
      {conError.map((p) => (
        <Alert key={p.id} tone="destructive">
          <span className="flex flex-wrap items-center justify-between gap-3">
            <span>
              No se pudo enviar la lista de {p.grupoNombre} ({p.fecha}): {p.error}
            </span>
            <Button size="sm" variant="outline" onClick={() => pendientes.quitar(p.id)}>
              Descartar
            </Button>
          </span>
        </Alert>
      ))}
      {aviso && enLinea && porEnviar.length === 0 ? <Alert tone="success">{aviso}</Alert> : null}
    </div>
  )
}

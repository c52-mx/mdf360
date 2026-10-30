import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { QRCodeSVG } from 'qrcode.react'
import { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  CardDescription,
  CardTitle,
  ConfirmButton,
  useToast,
} from '@/design-system'
import { api } from '@/lib/api'

interface Pendiente {
  id: number
  nombre: string
  whatsapp: string
  estado: string
  whatsapp_url: string
}

interface Props {
  grupoId: number
  /** Ruta del enlace actual (ej. /unirse/abc) o null si no hay. */
  enlace: string | null
  suspendido: boolean
  /** Dentro de otra tarjeta (p. ej. «Sumar gente»): sin marco propio. */
  embebida?: boolean
}

/** Enlace y QR para que alguien pida entrar al grupo; el líder aprueba como en una sala de espera. */
export function IngresoCard({ grupoId, enlace, suspendido, embebida = false }: Props) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [aprobada, setAprobada] = useState<Pendiente | null>(null)

  const refrescar = () => {
    void queryClient.invalidateQueries({ queryKey: ['grupo', String(grupoId)] })
    void queryClient.invalidateQueries({ queryKey: ['solicitudes', grupoId] })
  }

  const solicitudes = useQuery({
    queryKey: ['solicitudes', grupoId],
    queryFn: () => api<Pendiente[]>(`/api/grupos/${grupoId}/solicitudes/`),
    refetchInterval: 15_000,
  })

  const generar = useMutation({
    mutationFn: () => api(`/api/grupos/${grupoId}/enlace/`, { method: 'POST', body: {} }),
    onSuccess: refrescar,
  })
  const desactivar = useMutation({
    mutationFn: () => api(`/api/grupos/${grupoId}/enlace/`, { method: 'DELETE' }),
    onSuccess: () => {
      toast.mostrar('El enlace quedó desactivado.')
      refrescar()
    },
  })
  const resolver = useMutation({
    mutationFn: ({ id, aprobar }: { id: number; aprobar: boolean }) =>
      api<Pendiente>(`/api/grupos/solicitudes/${id}/${aprobar ? 'aprobar' : 'rechazar'}/`, {
        method: 'POST',
        body: {},
      }),
    onSuccess: (s, { aprobar }) => {
      if (aprobar) {
        setAprobada(s)
        toast.mostrar(`${s.nombre} ya es parte del grupo.`)
      }
      refrescar()
      void queryClient.invalidateQueries({ queryKey: ['grupos'] })
    },
  })

  const url = enlace ? `${window.location.origin}${enlace}` : ''
  const copiar = async () => {
    await navigator.clipboard.writeText(url)
    toast.mostrar('Enlace copiado.')
  }
  const error = generar.error ?? desactivar.error ?? resolver.error ?? solicitudes.error

  const Marco = embebida ? 'div' : Card
  return (
    <Marco className={embebida ? 'flex flex-col gap-4 border-t border-border pt-4' : 'flex flex-col gap-4'}>
      <div className="flex flex-col gap-1">
        <CardTitle>Invitar por enlace o QR</CardTitle>
        <CardDescription>
          Comparte el enlace o el QR. Quien lo abra deja su nombre y WhatsApp y espera; entra al grupo hasta
          que tú lo apruebes.
        </CardDescription>
      </div>
      {error ? <Alert tone="destructive">{error.message}</Alert> : null}

      {enlace ? (
        <div className="flex flex-wrap items-start gap-6">
          <div className="rounded-card bg-card p-3 ring-1 ring-border">
            <QRCodeSVG value={url} size={160} role="img" aria-label="Código QR del grupo" />
          </div>
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <p className="break-all font-semibold">{url}</p>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={() => void copiar()}>
                Copiar enlace
              </Button>
              <ConfirmButton
                size="sm"
                variant="outline"
                pregunta="El enlace y el QR anteriores dejarán de servir. ¿Generar uno nuevo?"
                etiquetaConfirmar="Sí, generar"
                onConfirm={() => generar.mutate()}
              >
                Generar uno nuevo
              </ConfirmButton>
              <ConfirmButton
                size="sm"
                variant="outline"
                pregunta="¿Desactivar el enlace?"
                etiquetaConfirmar="Sí, desactivar"
                onConfirm={() => desactivar.mutate()}
              >
                Desactivar
              </ConfirmButton>
            </div>
          </div>
        </div>
      ) : (
        <div>
          <Button onClick={() => generar.mutate()} disabled={generar.isPending || suspendido}>
            Crear enlace y QR
          </Button>
          {suspendido ? <CardDescription>Un grupo suspendido no recibe solicitudes.</CardDescription> : null}
        </div>
      )}

      {aprobada ? (
        <Alert tone="success">
          <span className="flex flex-wrap items-center justify-between gap-2">
            {aprobada.nombre} ya es parte del grupo.
            <Button asChild size="sm" variant="success">
              <a href={aprobada.whatsapp_url} target="_blank" rel="noreferrer">
                Avisarle por WhatsApp
              </a>
            </Button>
          </span>
        </Alert>
      ) : null}

      <div className="flex flex-col gap-2">
        <h3 className="text-lg">Solicitudes pendientes</h3>
        {solicitudes.data?.length === 0 ? (
          <CardDescription>No hay solicitudes por ahora.</CardDescription>
        ) : null}
        <ul className="flex flex-col divide-y divide-border">
          {solicitudes.data?.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center gap-3 py-3">
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="font-semibold">{s.nombre}</span>
                <span className="text-sm text-muted-foreground">{s.whatsapp}</span>
              </div>
              <Button
                size="sm"
                onClick={() => resolver.mutate({ id: s.id, aprobar: true })}
                disabled={resolver.isPending}
              >
                Aprobar
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => resolver.mutate({ id: s.id, aprobar: false })}
                disabled={resolver.isPending}
              >
                Rechazar
              </Button>
            </li>
          ))}
        </ul>
      </div>
    </Marco>
  )
}

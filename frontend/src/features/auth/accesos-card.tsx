import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useDeferredValue, useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  Field,
  useToast,
} from '@/design-system'
import { api } from '@/lib/api'

interface Acceso {
  id: number
  nombre: string
  whatsapp: string
  bloqueado: boolean
  activada: boolean
}

interface Reinicio {
  user: { nombre: string }
  activation_url: string
  whatsapp_url: string
  expires_at: string
}

/** Desbloquear a quien se pasó de intentos o reiniciar su acceso (perdió su PIN o su número). */
export function AccesosCard() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [texto, setTexto] = useState('')
  const q = useDeferredValue(texto.trim())
  const [reinicio, setReinicio] = useState<Reinicio | null>(null)
  const [copiado, setCopiado] = useState(false)

  const accesos = useQuery({
    queryKey: ['accesos', q],
    queryFn: () => api<Acceso[]>(`/api/auth/accesos/?q=${encodeURIComponent(q)}`),
  })

  const desbloquear = useMutation({
    mutationFn: (a: Acceso) => api(`/api/auth/users/${a.id}/unlock/`, { method: 'POST' }),
    onSuccess: (_, a) => {
      toast.mostrar(`${a.nombre} ya puede intentar entrar de nuevo.`)
      void queryClient.invalidateQueries({ queryKey: ['accesos'] })
    },
  })

  const reiniciar = useMutation({
    mutationFn: (a: Acceso) => api<Reinicio>(`/api/auth/users/${a.id}/reset/`, { method: 'POST' }),
    onSuccess: (r) => {
      setReinicio(r)
      setCopiado(false)
    },
  })

  const copiar = async (url: string) => {
    await navigator.clipboard.writeText(url)
    setCopiado(true)
  }

  const error = desbloquear.error ?? reiniciar.error ?? accesos.error

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <CardTitle>Accesos de tu gente</CardTitle>
        <CardDescription>
          Si alguien ve «Demasiados intentos», desbloquéalo aquí. Si perdió su PIN o cambió de
          número, reinicia su acceso y envíale el enlace.
        </CardDescription>
      </div>
      <Field
        label="Buscar por nombre o WhatsApp"
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
      />
      {error ? <Alert tone="destructive">{error.message}</Alert> : null}
      {accesos.data?.length === 0 ? (
        <CardDescription>No hay personas con ese dato en tu alcance.</CardDescription>
      ) : null}
      <ul className="flex flex-col divide-y divide-border">
        {accesos.data?.map((a) => (
          <li key={a.id} className="flex flex-wrap items-center gap-3 py-3">
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="font-semibold">{a.nombre}</span>
              <span className="text-sm text-muted-foreground">{a.whatsapp}</span>
            </div>
            {a.bloqueado ? <Badge tone="destructive">Bloqueado</Badge> : null}
            {!a.activada ? <Badge tone="warning">Sin activar</Badge> : null}
            {a.bloqueado ? (
              <Button size="sm" onClick={() => desbloquear.mutate(a)} disabled={desbloquear.isPending}>
                Desbloquear
              </Button>
            ) : null}
            <Button
              size="sm"
              variant="outline"
              onClick={() => reiniciar.mutate(a)}
              disabled={reiniciar.isPending}
            >
              Reiniciar acceso
            </Button>
          </li>
        ))}
      </ul>
      {reinicio ? (
        <Alert tone="success">
          <div className="flex flex-col gap-3">
            <span>
              Enlace para {reinicio.user.nombre}: de un solo uso, caduca el{' '}
              {new Date(reinicio.expires_at).toLocaleString('es-MX')}.
            </span>
            <div className="flex flex-wrap gap-3">
              <Button asChild size="sm" variant="success">
                <a href={reinicio.whatsapp_url} target="_blank" rel="noreferrer">
                  Enviar por WhatsApp
                </a>
              </Button>
              <Button size="sm" variant="outline" onClick={() => void copiar(reinicio.activation_url)}>
                {copiado ? 'Enlace copiado' : 'Copiar enlace'}
              </Button>
            </div>
          </div>
        </Alert>
      ) : null}
    </Card>
  )
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useDeferredValue, useState } from 'react'
import { Alert, Badge, Button, Card, CardDescription, CardTitle, ComboField, useToast } from '@/design-system'
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
  const [elegido, setElegido] = useState('')
  const [reinicio, setReinicio] = useState<Reinicio | null>(null)
  const [copiado, setCopiado] = useState(false)

  const accesos = useQuery({
    queryKey: ['accesos', q],
    queryFn: () => api<Acceso[]>(`/api/auth/accesos/?q=${encodeURIComponent(q)}`),
  })
  const persona = accesos.data?.find((a) => String(a.id) === elegido)

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
          Si alguien ve «Demasiados intentos», desbloquéalo aquí. Si perdió su PIN o cambió de número,
          reinicia su acceso y envíale el enlace.
        </CardDescription>
      </div>
      <ComboField
        label="Buscar persona"
        options={(accesos.data ?? []).map((a) => ({ value: String(a.id), label: a.nombre, detalle: a.whatsapp }))}
        value={elegido}
        onChange={(v) => {
          setElegido(v)
          setReinicio(null)
        }}
        onBuscar={setTexto}
        filtrar={false}
        placeholder="Nombre o número de WhatsApp"
        vacio="No hay personas con ese dato en tu alcance."
      />
      {error ? <Alert tone="destructive">{error.message}</Alert> : null}
      {persona ? (
        <div className="flex flex-wrap items-center gap-3 rounded-control border border-border p-3">
          <div className="flex min-w-0 flex-1 flex-col">
            <span className="font-semibold">{persona.nombre}</span>
            <span className="text-sm text-muted-foreground">{persona.whatsapp}</span>
          </div>
          {persona.bloqueado ? <Badge tone="destructive">Bloqueado</Badge> : null}
          {!persona.activada ? <Badge tone="warning">Sin activar</Badge> : null}
          {persona.bloqueado ? (
            <Button size="sm" onClick={() => desbloquear.mutate(persona)} disabled={desbloquear.isPending}>
              Desbloquear
            </Button>
          ) : null}
          <Button size="sm" variant="outline" onClick={() => reiniciar.mutate(persona)} disabled={reiniciar.isPending}>
            Reiniciar acceso
          </Button>
        </div>
      ) : null}
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

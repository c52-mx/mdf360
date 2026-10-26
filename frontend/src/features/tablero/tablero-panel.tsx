import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pin, PinOff, Trash2 } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  CheckboxField,
  TextareaField,
  useToast,
} from '@/design-system'
import { api } from '@/lib/api'

export interface Mensaje {
  id: number
  origen: { tipo: string; id: number; etiqueta: string }
  autor: string
  texto: string
  fijado: boolean
  creado_en: string
  es_mio: boolean
  puede_moderar: boolean
}

interface Props {
  origenTipo: string
  origenId: number
  puedePublicar: boolean
  titulo?: string
}

/**
 * Tablero de mensajes de un origen (grupo, curso, área…). Reutilizable: solo necesita el tipo e
 * id del origen; el servidor decide quién publica y quién lee. Al abrirlo marca los mensajes
 * como vistos para el contador de no leídos.
 */
export function TableroPanel({ origenTipo, origenId, puedePublicar, titulo }: Props) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const clave = ['tablero', origenTipo, origenId]
  const [texto, setTexto] = useState('')
  const [fijar, setFijar] = useState(false)

  const mensajes = useQuery({
    queryKey: clave,
    queryFn: () => api<Mensaje[]>(`/api/tablero/?origen_tipo=${origenTipo}&origen_id=${origenId}`),
    retry: false,
  })
  const visto = useMutation({
    mutationFn: () =>
      api('/api/tablero/visto/', { method: 'POST', body: { origen_tipo: origenTipo, origen_id: origenId } }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['tablero-no-leidos'] }),
  })
  const marcar = visto.mutate
  const hayDatos = mensajes.isSuccess
  useEffect(() => {
    if (hayDatos) marcar()
  }, [hayDatos, marcar])

  const publicar = useMutation({
    mutationFn: () =>
      api('/api/tablero/', {
        method: 'POST',
        body: { origen_tipo: origenTipo, origen_id: origenId, texto, fijado: fijar },
      }),
    onSuccess: () => {
      setTexto('')
      setFijar(false)
      void queryClient.invalidateQueries({ queryKey: clave })
    },
  })
  const fijarMensaje = useMutation({
    mutationFn: ({ id, fijado }: { id: number; fijado: boolean }) =>
      api(`/api/tablero/${id}/`, { method: 'PATCH', body: { fijado } }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: clave }),
  })
  const restaurar = useMutation({
    mutationFn: (id: number) => api(`/api/tablero/${id}/restaurar/`, { method: 'POST', body: {} }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: clave }),
  })
  const restaurarMensaje = restaurar.mutate
  const borrar = useMutation({
    mutationFn: (id: number) => api(`/api/tablero/${id}/`, { method: 'DELETE' }),
    onSuccess: (_, id) => {
      void queryClient.invalidateQueries({ queryKey: clave })
      // Se borra al instante, pero se puede deshacer unos segundos
      toast.mostrar('Mensaje borrado.', { etiqueta: 'Deshacer', onClick: () => restaurarMensaje(id) })
    },
  })

  if (mensajes.isError) return null // sin permiso de lectura en este origen

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    publicar.mutate()
  }
  const lista = mensajes.data ?? []

  return (
    <Card className="flex flex-col gap-4">
      <CardTitle>{titulo ?? 'Tablero de mensajes'}</CardTitle>
      {mensajes.isSuccess && lista.length === 0 ? (
        <CardDescription>Todavía no hay mensajes.</CardDescription>
      ) : null}
      <ul className="flex flex-col gap-3">
        {lista.map((m) => (
          <li key={m.id} className="flex flex-col gap-1 rounded-control border border-border p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-bold">{m.autor}</span>
              <span className="flex items-center gap-2 text-sm text-muted-foreground">
                {m.fijado ? <Badge tone="primary">Fijado</Badge> : null}
                {new Date(m.creado_en).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' })}
              </span>
            </div>
            <p className="whitespace-pre-line">{m.texto}</p>
            {m.puede_moderar ? (
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => fijarMensaje.mutate({ id: m.id, fijado: !m.fijado })}
                >
                  {m.fijado ? <PinOff aria-hidden className="size-4" /> : <Pin aria-hidden className="size-4" />}
                  {m.fijado ? 'Quitar fijado' : 'Fijar'}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => borrar.mutate(m.id)}>
                  <Trash2 aria-hidden className="size-4" />
                  Borrar
                </Button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
      {fijarMensaje.error ? <Alert tone="destructive">{fijarMensaje.error.message}</Alert> : null}
      {borrar.error ? <Alert tone="destructive">{borrar.error.message}</Alert> : null}

      {puedePublicar ? (
        <form onSubmit={onSubmit} className="flex max-w-xl flex-col gap-3">
          <TextareaField
            label="Nuevo mensaje"
            maxLength={1000}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            hint={`${texto.length}/1000`}
            required
          />
          <CheckboxField checked={fijar} onChange={(e) => setFijar(e.target.checked)} label="Fijar arriba" />
          {publicar.error ? <Alert tone="destructive">{publicar.error.message}</Alert> : null}
          <Button type="submit" disabled={publicar.isPending || !texto.trim()}>
            Publicar
          </Button>
        </form>
      ) : null}
    </Card>
  )
}

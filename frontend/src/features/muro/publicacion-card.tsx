import { useMutation, useQuery, useQueryClient, type InfiniteData } from '@tanstack/react-query'
import { MessageCircle, Trash2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Alert, Badge, Button, Card, Field } from '@/design-system'
import { api } from '@/lib/api'
import { cn } from '@/lib/cn'
import { Acciones, CLAVE_MURO, Edicion } from './acciones-publicacion'
import {
  REACCIONES,
  type Comentario,
  type PaginaMuro,
  type Publicacion,
  type TipoReaccion,
} from './types'

function fecha(iso: string): string {
  return new Date(iso).toLocaleString('es-MX', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function Comentarios({ publicacion }: { publicacion: Publicacion }) {
  const queryClient = useQueryClient()
  const clave = ['muro', 'comentarios', publicacion.id]
  const [texto, setTexto] = useState('')
  const lista = useQuery({
    queryKey: clave,
    queryFn: () => api<Comentario[]>(`/api/muro/${publicacion.id}/comentarios/`),
  })
  const refrescar = () => {
    void queryClient.invalidateQueries({ queryKey: clave })
    void queryClient.invalidateQueries({ queryKey: CLAVE_MURO })
  }
  const comentar = useMutation({
    mutationFn: () =>
      api(`/api/muro/${publicacion.id}/comentarios/`, {
        method: 'POST',
        body: { texto },
      }),
    onSuccess: () => {
      setTexto('')
      refrescar()
    },
  })
  const quitar = useMutation({
    mutationFn: (id: number) => api(`/api/muro/comentarios/${id}/`, { method: 'DELETE' }),
    onSuccess: refrescar,
  })
  const enviar = (e: FormEvent) => {
    e.preventDefault()
    if (texto.trim()) comentar.mutate()
  }
  return (
    <div className="flex flex-col gap-3 border-t border-border pt-3">
      <ul className="flex flex-col gap-2">
        {(lista.data ?? []).map((c) => (
          <li key={c.id} className="flex flex-col gap-0.5 rounded-control bg-muted p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-bold">{c.autor}</span>
              <span className="text-sm text-muted-foreground">{fecha(c.creado_en)}</span>
            </div>
            <p className="whitespace-pre-line">{c.texto}</p>
            {c.puede_quitar ? (
              <button
                type="button"
                onClick={() => quitar.mutate(c.id)}
                className="presionable flex h-11 w-fit items-center gap-1 text-sm font-semibold text-muted-foreground hover:text-foreground"
              >
                <Trash2 aria-hidden className="size-4" />
                Quitar
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      <form onSubmit={enviar} className="flex items-end gap-2">
        <div className="flex-1">
          <Field
            label="Escribe un comentario"
            value={texto}
            maxLength={500}
            onChange={(e) => setTexto(e.target.value)}
          />
        </div>
        <Button type="submit" disabled={comentar.isPending || !texto.trim()}>
          Comentar
        </Button>
      </form>
      {comentar.error ? <Alert tone="destructive">{comentar.error.message}</Alert> : null}
      {quitar.error ? <Alert tone="destructive">{quitar.error.message}</Alert> : null}
    </div>
  )
}

/** Una publicación del muro: audiencias, texto, reacciones y comentarios. Solo contenido. */
export function PublicacionCard({ publicacion: p }: { publicacion: Publicacion }) {
  const queryClient = useQueryClient()
  const [verComentarios, setVerComentarios] = useState(false)
  const [editando, setEditando] = useState(false)

  const reaccionar = useMutation({
    mutationFn: (tipo: TipoReaccion) =>
      api<Publicacion>(`/api/muro/${p.id}/reaccion/`, {
        method: 'PUT',
        body: { tipo },
      }),
    onSuccess: (nueva) => {
      // Se refleja al instante en la lista, sin volver a pedir todo el muro
      queryClient.setQueriesData<InfiniteData<PaginaMuro>>({ queryKey: CLAVE_MURO }, (datos) =>
        datos
          ? {
              ...datos,
              pages: datos.pages.map((pg) => ({
                ...pg,
                fijadas: pg.fijadas.map((x) => (x.id === nueva.id ? nueva : x)),
                resultados: pg.resultados.map((x) => (x.id === nueva.id ? nueva : x)),
              })),
            }
          : datos,
      )
    },
  })

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-bold">{p.autor}</span>
        <span className="flex items-center gap-2 text-sm text-muted-foreground">
          {p.fijada ? <Badge tone="primary">Fijada</Badge> : null}
          {fecha(p.creada_en)}
          {p.editada ? ' · editada' : ''}
        </span>
      </div>
      <ul aria-label="Dirigida a" className="flex flex-wrap gap-1">
        {p.audiencias.map((a) => (
          <li key={`${a.tipo}-${a.id}`}>
            <Badge tone="primary">{a.etiqueta}</Badge>
          </li>
        ))}
      </ul>
      {editando ? (
        <Edicion publicacion={p} onTerminar={() => setEditando(false)} />
      ) : (
        <p className="whitespace-pre-line">{p.texto}</p>
      )}
      <div className="flex flex-wrap items-center gap-1">
        {REACCIONES.map(({ tipo, icono, nombre }) => {
          const activa = p.mi_reaccion === tipo
          const n = p.reacciones[tipo] ?? 0
          return (
            <button
              key={tipo}
              type="button"
              aria-pressed={activa}
              aria-label={`${nombre}${n ? `, ${n}` : ''}`}
              onClick={() => reaccionar.mutate(tipo)}
              className={cn(
                'presionable flex h-11 min-w-11 items-center justify-center gap-1 rounded-full px-3 text-sm font-semibold',
                activa ? 'bg-primary-soft text-primary' : 'text-muted-foreground hover:bg-muted',
              )}
            >
              <span aria-hidden>{icono}</span>
              {n > 0 ? n : null}
            </button>
          )
        })}
        <button
          type="button"
          aria-expanded={verComentarios}
          onClick={() => setVerComentarios((v) => !v)}
          className="presionable ml-auto flex h-11 items-center gap-1 rounded-full px-3 text-sm font-semibold text-muted-foreground hover:bg-muted"
        >
          <MessageCircle aria-hidden className="size-5" />
          {p.comentarios_total > 0 ? `${p.comentarios_total} comentarios` : 'Comentar'}
        </button>
      </div>
      <Acciones publicacion={p} onEditar={() => setEditando(true)} />
      {reaccionar.error ? <Alert tone="destructive">{reaccionar.error.message}</Alert> : null}
      {verComentarios ? <Comentarios publicacion={p} /> : null}
    </Card>
  )
}

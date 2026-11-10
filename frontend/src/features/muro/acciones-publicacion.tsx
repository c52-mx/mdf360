import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Flag, Pencil, Pin, PinOff, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Alert, Button, ConfirmButton, Field, TextareaField } from '@/design-system'
import { api } from '@/lib/api'
import type { Publicacion } from './types'

export const CLAVE_MURO = ['muro']

/** Editar, fijar, eliminar y reportar: cada quien ve solo lo que puede hacer. */
export function Acciones({
  publicacion: p,
  onEditar,
}: {
  publicacion: Publicacion
  onEditar: () => void
}) {
  const queryClient = useQueryClient()
  const [reportando, setReportando] = useState(false)
  const [motivo, setMotivo] = useState('')
  const refrescar = () => void queryClient.invalidateQueries({ queryKey: CLAVE_MURO })
  const fijar = useMutation({
    mutationFn: () =>
      api(`/api/muro/${p.id}/`, {
        method: 'PATCH',
        body: { fijada: !p.fijada },
      }),
    onSuccess: refrescar,
  })
  const eliminar = useMutation({
    mutationFn: () => api(`/api/muro/${p.id}/`, { method: 'DELETE' }),
    onSuccess: refrescar,
  })
  const reportar = useMutation({
    mutationFn: () => api(`/api/muro/${p.id}/reportar/`, { method: 'POST', body: { motivo } }),
    onSuccess: () => {
      setReportando(false)
      refrescar()
    },
  })
  const atender = useMutation({
    mutationFn: () => api(`/api/muro/${p.id}/atender-reportes/`, { method: 'POST', body: {} }),
    onSuccess: refrescar,
  })
  const puedeReportar = !p.es_mia && !p.yo_reporte
  const hayAlgo =
    p.puede_editar || p.puede_quitar || p.puede_moderar || puedeReportar || p.yo_reporte
  if (!hayAlgo) return null
  const errores = [fijar.error, eliminar.error, reportar.error, atender.error].filter(Boolean)
  return (
    <div className="flex flex-col gap-2 border-t border-border pt-2">
      <div className="flex flex-wrap items-center gap-1">
        {p.puede_editar ? (
          <Button size="sm" variant="ghost" onClick={onEditar}>
            <Pencil aria-hidden className="size-4" />
            Editar
          </Button>
        ) : null}
        {p.puede_moderar ? (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => fijar.mutate()}
            disabled={fijar.isPending}
          >
            {p.fijada ? (
              <PinOff aria-hidden className="size-4" />
            ) : (
              <Pin aria-hidden className="size-4" />
            )}
            {p.fijada ? 'Quitar fijado' : 'Fijar'}
          </Button>
        ) : null}
        {p.puede_quitar ? (
          <ConfirmButton
            size="sm"
            variant="ghost"
            pregunta="¿Eliminar esta publicación?"
            etiquetaConfirmar="Sí, eliminar"
            onConfirm={() => eliminar.mutate()}
          >
            <Trash2 aria-hidden className="size-4" />
            Eliminar
          </ConfirmButton>
        ) : null}
        {puedeReportar ? (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setReportando((v) => !v)}
            aria-expanded={reportando}
          >
            <Flag aria-hidden className="size-4" />
            Reportar
          </Button>
        ) : null}
        {!p.es_mia && p.yo_reporte ? (
          <span className="text-sm text-muted-foreground">Ya la reportaste</span>
        ) : null}
      </div>
      {p.puede_moderar && p.reportes > 0 ? (
        <Alert tone="warning">
          <span className="flex flex-wrap items-center justify-between gap-2">
            {p.reportes === 1 ? '1 persona la reportó.' : `${p.reportes} personas la reportaron.`}
            <Button
              size="sm"
              variant="outline"
              onClick={() => atender.mutate()}
              disabled={atender.isPending}
            >
              Marcar como revisada
            </Button>
          </span>
        </Alert>
      ) : null}
      {reportando ? (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            reportar.mutate()
          }}
          className="flex items-end gap-2"
        >
          <div className="flex-1">
            <Field
              label="¿Por qué la reportas? (opcional)"
              value={motivo}
              maxLength={300}
              onChange={(e) => setMotivo(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={reportar.isPending}>
            Enviar reporte
          </Button>
        </form>
      ) : null}
      {errores.map((e, i) => (
        <Alert key={i} tone="destructive">
          {e?.message}
        </Alert>
      ))}
    </div>
  )
}

export function Edicion({
  publicacion: p,
  onTerminar,
}: {
  publicacion: Publicacion
  onTerminar: () => void
}) {
  const queryClient = useQueryClient()
  const [texto, setTexto] = useState(p.texto)
  const guardar = useMutation({
    mutationFn: () => api(`/api/muro/${p.id}/`, { method: 'PATCH', body: { texto } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: CLAVE_MURO })
      onTerminar()
    },
  })
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        guardar.mutate()
      }}
      className="flex flex-col gap-2"
    >
      <TextareaField
        label="Editar publicación"
        maxLength={2000}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
      />
      {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={guardar.isPending || !texto.trim()}>
          Guardar
        </Button>
        <Button type="button" variant="ghost" onClick={onTerminar}>
          Cancelar
        </Button>
      </div>
    </form>
  )
}

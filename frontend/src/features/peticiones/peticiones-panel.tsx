import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Alert, Badge, Button, Card, CardDescription, CardTitle } from '@/design-system'
import { api } from '@/lib/api'
import { FormularioDinamico } from './formulario-dinamico'
import { OrigenBadge } from './origen-badge'
import type { Formulario, Pagina, Peticion, Valores } from './types'

interface Props {
  origenTipo: string
  origenId: number
  /** Reunión, curso o evento concreto dentro del origen (opcional). */
  referenciaId?: number
  /** Si la persona puede capturar peticiones en este origen (el servidor lo vuelve a validar). */
  puedeRegistrar: boolean
  titulo?: string
}

export const etiquetasDe = (f?: Formulario) =>
  Object.fromEntries((f?.campos ?? []).map((c) => [c.clave, c.etiqueta]))

export function useFormularioPeticiones() {
  return useQuery({
    queryKey: ['peticiones-formulario'],
    queryFn: () => api<Formulario>('/api/peticiones/formulario/'),
  })
}

/** Contenido de una petición con su origen, siempre visible. */
export function PeticionItem({
  p,
  etiquetas,
  onEstado,
}: {
  p: Peticion
  etiquetas: Record<string, string>
  onEstado?: (id: number, estado: 'activa' | 'atendida') => void
}) {
  return (
    <div className="flex flex-col gap-2 rounded-control border border-border p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <OrigenBadge origen={p.origen} />
        <Badge tone={p.estado === 'atendida' ? 'success' : 'warning'}>{p.estado_display}</Badge>
      </div>
      {p.ilegible ? (
        <Alert tone="warning">No se puede leer esta petición (cambió la clave de cifrado).</Alert>
      ) : p.datos ? (
        <dl className="flex flex-col gap-1">
          {Object.entries(p.datos)
            .filter(([, v]) => v !== '' && v !== false)
            .map(([clave, valor]) => (
              <div key={clave}>
                <dt className="text-sm text-muted-foreground">{etiquetas[clave] ?? clave}</dt>
                <dd className="whitespace-pre-line">{valor === true ? 'Sí' : String(valor)}</dd>
              </div>
            ))}
        </dl>
      ) : null}
      <CardDescription>
        Registrada el {new Date(p.creada_en).toLocaleDateString('es-MX')} · se borra el{' '}
        {new Date(p.expira_en).toLocaleDateString('es-MX')}
      </CardDescription>
      {onEstado ? (
        <div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onEstado(p.id, p.estado === 'activa' ? 'atendida' : 'activa')}
          >
            {p.estado === 'activa' ? 'Marcar como atendida' : 'Reactivar'}
          </Button>
        </div>
      ) : null}
    </div>
  )
}

/**
 * Peticiones de oración de un origen (grupo, curso, evento…): captura y consulta.
 * Reutilizable: solo necesita el tipo e id del origen. El servidor decide quién ve qué.
 */
export function PeticionesPanel({ origenTipo, origenId, referenciaId, puedeRegistrar, titulo }: Props) {
  const queryClient = useQueryClient()
  const formulario = useFormularioPeticiones()
  const clave = ['peticiones', origenTipo, origenId]
  const lista = useQuery({
    queryKey: clave,
    queryFn: () =>
      api<Pagina<Peticion>>(`/api/peticiones/?origen_tipo=${origenTipo}&origen_id=${origenId}&estado=activa`),
    retry: false,
  })
  const [valores, setValores] = useState<Valores>({})
  const [confirmada, setConfirmada] = useState(false)

  const registrar = useMutation({
    mutationFn: () =>
      api('/api/peticiones/', {
        method: 'POST',
        body: { origen_tipo: origenTipo, origen_id: origenId, referencia_id: referenciaId, datos: valores },
      }),
    onSuccess: () => {
      setValores({})
      setConfirmada(true)
      void queryClient.invalidateQueries({ queryKey: clave })
    },
  })
  const estado = useMutation({
    mutationFn: ({ id, estado: nuevo }: { id: number; estado: 'activa' | 'atendida' }) =>
      api(`/api/peticiones/${id}/`, { method: 'PATCH', body: { estado: nuevo } }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: clave }),
  })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    setConfirmada(false)
    registrar.mutate()
  }
  const peticiones = lista.data?.results ?? []
  const etiquetas = etiquetasDe(formulario.data)

  if (!puedeRegistrar && peticiones.length === 0) return null // sin permiso de ver ni de capturar

  return (
    <Card className="flex flex-col gap-4">
      <CardTitle>{titulo ?? 'Peticiones de oración'}</CardTitle>
      {peticiones.length > 0 ? (
        <ul className="flex flex-col gap-3">
          {peticiones.map((p) => (
            <li key={p.id}>
              <PeticionItem
                p={p}
                etiquetas={etiquetas}
                onEstado={(id, nuevo) => estado.mutate({ id, estado: nuevo })}
              />
            </li>
          ))}
        </ul>
      ) : lista.isSuccess ? (
        <CardDescription>No hay peticiones activas.</CardDescription>
      ) : null}
      {estado.error ? <Alert tone="destructive">{estado.error.message}</Alert> : null}

      {puedeRegistrar && formulario.data ? (
        <form onSubmit={onSubmit} className="flex max-w-xl flex-col gap-4">
          <CardTitle>Registrar una petición</CardTitle>
          <FormularioDinamico
            campos={formulario.data.campos}
            valores={valores}
            onChange={(v) => {
              setConfirmada(false)
              setValores(v)
            }}
          />
          {confirmada ? <Alert tone="success">Petición registrada.</Alert> : null}
          {registrar.error ? <Alert tone="destructive">{registrar.error.message}</Alert> : null}
          <Button type="submit" disabled={registrar.isPending}>
            Guardar petición
          </Button>
          <CardDescription>
            Es confidencial: solo la ven el Líder y los superiores, y se borra automáticamente.
          </CardDescription>
        </form>
      ) : null}
    </Card>
  )
}

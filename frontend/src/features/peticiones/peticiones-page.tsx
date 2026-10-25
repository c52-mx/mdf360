import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Button, Card, PageHeader, SelectField } from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'
import { etiquetasDe, PeticionItem, useFormularioPeticiones } from './peticiones-panel'
import type { Pagina, Peticion } from './types'

/** Todas las peticiones que la persona puede ver, de cualquier origen, siempre con su origen. */
export function PeticionesPage() {
  const queryClient = useQueryClient()
  const puedeConfigurar = useCan('peticiones.configurar')
  const [origen, setOrigen] = useState('')
  const [estado, setEstado] = useState('activa')
  const [page, setPage] = useState(1)

  const origenes = useQuery({
    queryKey: ['peticiones-origenes'],
    queryFn: () => api<{ tipo: string; nombre: string }[]>('/api/peticiones/origenes/'),
  })
  const formulario = useFormularioPeticiones()
  const lista = useQuery({
    queryKey: ['peticiones', 'todas', { origen, estado, page }],
    placeholderData: (previo) => previo,
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page) })
      if (origen) params.set('origen_tipo', origen)
      if (estado) params.set('estado', estado)
      return api<Pagina<Peticion>>(`/api/peticiones/?${params.toString()}`)
    },
  })
  const cambiar = useMutation({
    mutationFn: ({ id, estado: nuevo }: { id: number; estado: 'activa' | 'atendida' }) =>
      api(`/api/peticiones/${id}/`, { method: 'PATCH', body: { estado: nuevo } }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['peticiones'] }),
  })
  const etiquetas = etiquetasDe(formulario.data)

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Peticiones de oración"
        description="Confidenciales. Cada una indica de dónde viene."
        module="grupos"
        actions={
          puedeConfigurar ? (
            <Button asChild variant="outline">
              <Link to="/peticiones/formulario">Editar formulario</Link>
            </Button>
          ) : null
        }
      />
      <Card className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <SelectField
          label="Origen"
          value={origen}
          onChange={(e) => {
            setOrigen(e.target.value)
            setPage(1)
          }}
          options={[
            { value: '', label: 'Todos los orígenes' },
            ...(origenes.data ?? []).map((o) => ({ value: o.tipo, label: o.nombre })),
          ]}
        />
        <SelectField
          label="Estado"
          value={estado}
          onChange={(e) => {
            setEstado(e.target.value)
            setPage(1)
          }}
          options={[
            { value: 'activa', label: 'Activas' },
            { value: 'atendida', label: 'Atendidas' },
            { value: '', label: 'Todas' },
          ]}
        />
      </Card>

      {lista.isError ? <Alert tone="destructive">{lista.error.message}</Alert> : null}
      {cambiar.error ? <Alert tone="destructive">{cambiar.error.message}</Alert> : null}
      {lista.data && lista.data.results.length === 0 ? <Alert>No hay peticiones con esos filtros.</Alert> : null}
      <ul className="flex flex-col gap-3">
        {lista.data?.results.map((p) => (
          <li key={p.id}>
            <PeticionItem p={p} etiquetas={etiquetas} onEstado={(id, nuevo) => cambiar.mutate({ id, estado: nuevo })} />
          </li>
        ))}
      </ul>
      {lista.data && (lista.data.next || lista.data.previous) ? (
        <div className="flex items-center justify-between">
          <Button variant="outline" disabled={!lista.data.previous} onClick={() => setPage((n) => n - 1)}>
            Anterior
          </Button>
          <span className="text-muted-foreground">Página {page}</span>
          <Button variant="outline" disabled={!lista.data.next} onClick={() => setPage((n) => n + 1)}>
            Siguiente
          </Button>
        </div>
      ) : null}
    </div>
  )
}

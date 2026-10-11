import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert, Button, Card, CardDescription, Field, PageHeader } from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'

interface Evento {
  id: number
  fecha: string
  accion: string
  actor: string
  objeto: string
  detalle: Record<string, unknown>
  ip: string | null
}
interface Pagina {
  count: number
  next: string | null
  previous: string | null
  results: Evento[]
}

export function AuditoriaPage() {
  const puede = useCan('bitacora.ver')
  const [accion, setAccion] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)

  const lista = useQuery({
    queryKey: ['auditoria', { accion, q, page }],
    enabled: puede,
    placeholderData: (previo) => previo,
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page) })
      if (accion.trim()) params.set('action', accion.trim())
      if (q.trim()) params.set('q', q.trim())
      return api<Pagina>(`/api/auditoria/?${params.toString()}`)
    },
  })

  if (!puede) return <Alert tone="warning">No tienes permiso para ver la bitácora.</Alert>

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Bitácora"
        description="Registro de solo lectura de lo que ocurre en el sistema. Consultarla también queda registrado."
        module="admin"
      />
      <Card className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Field
          label="Acción"
          placeholder="Ej. auth, persona, rbac"
          value={accion}
          onChange={(e) => {
            setAccion(e.target.value)
            setPage(1)
          }}
        />
        <Field
          label="Persona o número de objeto"
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(1)
          }}
        />
      </Card>
      {lista.isError ? <Alert tone="destructive">{lista.error.message}</Alert> : null}
      {lista.data ? (
        <>
          <p className="text-muted-foreground">{lista.data.count} eventos</p>
          <ul className="flex flex-col gap-2">
            {lista.data.results.map((e) => (
              <li key={e.id}>
                <Card className="flex flex-col gap-1">
                  <p className="font-bold">{e.accion}</p>
                  <CardDescription>
                    {new Date(e.fecha).toLocaleString('es-MX')} · {e.actor || 'Sistema'}
                    {e.objeto ? ` · ${e.objeto}` : ''}
                  </CardDescription>
                  {Object.keys(e.detalle).length > 0 ? (
                    <CardDescription>{JSON.stringify(e.detalle)}</CardDescription>
                  ) : null}
                </Card>
              </li>
            ))}
          </ul>
          <div className="flex items-center justify-between">
            <Button variant="outline" disabled={!lista.data.previous} onClick={() => setPage((n) => n - 1)}>
              Anterior
            </Button>
            <span className="text-muted-foreground">Página {page}</span>
            <Button variant="outline" disabled={!lista.data.next} onClick={() => setPage((n) => n + 1)}>
              Siguiente
            </Button>
          </div>
        </>
      ) : null}
    </div>
  )
}

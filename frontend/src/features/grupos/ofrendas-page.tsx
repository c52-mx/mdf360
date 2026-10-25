import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert, Badge, Button, Card, CardDescription, CardTitle, PageHeader } from '@/design-system'
import { api } from '@/lib/api'
import { fechaLarga } from './types'
import { AvalForm, dinero, estadoTone, type Ofrenda } from './ofrendas'

/** Pantalla del Tesorero: ofrendas pendientes de aval (o con diferencia) de sus grupos. */
export function OfrendasPage() {
  const queryClient = useQueryClient()
  const [abierta, setAbierta] = useState<number | null>(null)
  const pendientes = useQuery({
    queryKey: ['ofrendas-pendientes'],
    queryFn: () => api<Ofrenda[]>('/api/grupos/ofrendas/pendientes/'),
  })

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Ofrendas por avalar"
        description="Cuenta la ofrenda, escribe tu cifra y confirma con tu PIN."
        module="grupos"
      />
      {pendientes.isError ? <Alert tone="destructive">{pendientes.error.message}</Alert> : null}
      {pendientes.data && pendientes.data.length === 0 ? (
        <Alert tone="success">No tienes ofrendas pendientes.</Alert>
      ) : null}
      <ul className="flex flex-col gap-3">
        {pendientes.data?.map((o) => (
          <li key={o.id}>
            <Card className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <CardTitle>{o.grupo}</CardTitle>
                  <CardDescription className="capitalize">
                    {fechaLarga(o.fecha)} · {o.tipo_display}
                    {o.concepto ? ` · ${o.concepto}` : ''}
                  </CardDescription>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className="font-display text-2xl font-bold">{dinero(o.monto)}</span>
                  <Badge tone={estadoTone[o.estado]}>{o.estado_display}</Badge>
                </div>
              </div>
              {abierta === o.id ? (
                <AvalForm
                  ofrenda={o}
                  onListo={() => {
                    setAbierta(null)
                    void queryClient.invalidateQueries({ queryKey: ['ofrendas-pendientes'] })
                  }}
                />
              ) : (
                <div>
                  <Button onClick={() => setAbierta(o.id)}>Contar y avalar</Button>
                </div>
              )}
            </Card>
          </li>
        ))}
      </ul>
    </div>
  )
}

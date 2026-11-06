import { useQuery } from '@tanstack/react-query'
import { Alert, Card, CardDescription, CardTitle, DataTable, LineChart, type DataColumn } from '@/design-system'
import { api } from '@/lib/api'
import type { PanelUnidad } from './types'

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
const mesCorto = (aaaamm: string) => MESES[Number(aaaamm.slice(5, 7)) - 1] ?? aaaamm

function Dato({ titulo, valor, nota }: { titulo: string; valor: string | number; nota?: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <CardDescription>{titulo}</CardDescription>
      <span className="font-display text-2xl font-bold">{valor}</span>
      {nota ? <CardDescription>{nota}</CardDescription> : null}
    </Card>
  )
}

const columnas: DataColumn<PanelUnidad['por_rol'][number]>[] = [
  { clave: 'rol', titulo: 'Rol', orden: (r) => r.rol_display, celda: (r) => r.rol_display },
  { clave: 'total', titulo: 'Personas', numerica: true, orden: (r) => r.total, celda: (r) => r.total },
]

/** Dashboard de un ministerio para los roles superiores: gente, crecimiento, mensajes y peticiones. */
export function PanelUnidadCard({ unidadId }: { unidadId: number }) {
  const panel = useQuery({
    queryKey: ['unidad-panel', unidadId],
    queryFn: () => api<PanelUnidad>(`/api/unidades/${unidadId}/panel/`),
  })
  if (panel.isPending) return <p className="text-muted-foreground">Cargando el panel…</p>
  if (panel.isError) return <Alert tone="destructive">{panel.error.message}</Alert>
  const p = panel.data
  const ultimo = p.ultimo_mensaje ? new Date(p.ultimo_mensaje).toLocaleDateString('es-MX') : 'Sin mensajes'

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Dato titulo="Integrantes" valor={p.integrantes} nota={`${p.salieron} ya no sirven`} />
        <Dato titulo="Nuevos en 30 días" valor={p.nuevos_30_dias} />
        <Dato titulo="Peticiones" valor={p.peticiones.activas} nota={`${p.peticiones.atendidas} atendidas`} />
        <Dato titulo="Último mensaje" valor={ultimo} />
      </div>
      <Card className="flex flex-col gap-3">
        <CardTitle>Crecimiento y comunicación</CardTitle>
        <LineChart
          titulo="Personas que se sumaron y mensajes por mes"
          series={[
            { nombre: 'Se sumaron', puntos: p.meses.map((m) => ({ etiqueta: mesCorto(m.mes), valor: m.sumaron })) },
            { nombre: 'Mensajes', puntos: p.meses.map((m) => ({ etiqueta: mesCorto(m.mes), valor: m.mensajes })) },
          ]}
        />
      </Card>
      <Card className="flex flex-col gap-3">
        <CardTitle>Equipo por rol</CardTitle>
        <DataTable
          titulo="Equipo por rol"
          columnas={columnas}
          filas={p.por_rol}
          clave={(r) => r.rol}
          vacio="Todavía no hay integrantes."
        />
      </Card>
    </div>
  )
}

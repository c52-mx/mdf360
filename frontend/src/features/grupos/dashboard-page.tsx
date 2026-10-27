import { useQuery } from '@tanstack/react-query'
import { CalendarX, TrendingDown, TriangleAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  ColumnsChart,
  Meter,
} from '@/design-system'
import { api } from '@/lib/api'
import { dinero } from './ofrendas'

interface Tarjeta {
  id: number
  nombre: string
  integrantes: number
  reuniones_8_semanas: number
  asistencia_pct: number | null
  ultimas: { fecha: string; presentes: number; registrados: number }[]
  ultima_reunion: string | null
  sin_lista_esta_semana: boolean
  ofrendas: { avalado_30_dias: string; pendientes: number; con_diferencia: number } | null
  peticiones_activas: number | null
}

interface Alerta {
  tipo: 'sin_lista' | 'asistencia_baja' | 'ofrenda_con_diferencia'
  grupo_id: number
  grupo: string
  valor?: number
}

interface Dashboard {
  resumen: {
    grupos: number
    integrantes: number
    asistencia_pct: number | null
    alertas: number
    asistencia_minima_pct: number
  }
  serie: { semana: string; presentes: number; registrados: number; pct: number | null }[]
  grupos: Tarjeta[]
  alertas: Alerta[]
  suspendidos: { id: number; nombre: string; motivo: string }[]
}

const textoAlerta = (a: Alerta, minimo: number) =>
  a.tipo === 'sin_lista'
    ? `${a.grupo}: todavía no hay lista de asistencia esta semana.`
    : a.tipo === 'asistencia_baja'
      ? `${a.grupo}: asistencia de ${a.valor}%, por debajo del mínimo de ${minimo}%.`
      : `${a.grupo}: ${a.valor === 1 ? '1 ofrenda con diferencia' : `${a.valor} ofrendas con diferencia`}.`

const iconoAlerta = { sin_lista: CalendarX, asistencia_baja: TrendingDown, ofrenda_con_diferencia: TriangleAlert }

const corta = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })

const tonoAsistencia = (pct: number | null, minimo: number) =>
  pct === null ? 'primary' : pct < minimo ? 'destructive' : 'success'

/** Salud de los grupos que la persona puede consultar. Se muestra en Inicio. */
export function ResumenGrupos() {
  const datos = useQuery({
    queryKey: ['grupos-dashboard'],
    queryFn: () => api<Dashboard>('/api/grupos/dashboard/'),
  })
  if (datos.isPending) return <p className="text-muted-foreground">Cargando…</p>
  if (datos.isError) return <Alert tone="destructive">{datos.error.message}</Alert>
  const { resumen, serie, grupos, alertas, suspendidos = [] } = datos.data
  const minimo = resumen.asistencia_minima_pct

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl">Resumen de grupos</h2>
        <Button asChild variant="outline">
          <Link to="/grupos">Ver grupos</Link>
        </Button>
      </div>

      {grupos.length === 0 ? <Alert>Todavía no tienes grupos que supervisar.</Alert> : null}
      {suspendidos.length > 0 ? (
        <Alert tone="warning">
          {suspendidos.length === 1 ? '1 grupo suspendido' : `${suspendidos.length} grupos suspendidos`}:{' '}
          {suspendidos.map((s, i) => (
            <span key={s.id}>
              {i > 0 ? ', ' : ''}
              <Link className="underline" to={`/grupos/${s.id}`}>
                {s.nombre}
              </Link>
            </span>
          ))}
          .
        </Alert>
      ) : null}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Card>
          <CardDescription>Grupos</CardDescription>
          <p className="font-display text-3xl font-bold">{resumen.grupos}</p>
        </Card>
        <Card>
          <CardDescription>Integrantes</CardDescription>
          <p className="font-display text-3xl font-bold">{resumen.integrantes}</p>
        </Card>
        <Card>
          <CardDescription>Asistencia (4 semanas)</CardDescription>
          <p className="font-display text-3xl font-bold">
            {resumen.asistencia_pct === null ? 'Sin datos' : `${resumen.asistencia_pct}%`}
          </p>
        </Card>
        <Card>
          <CardDescription>Avisos</CardDescription>
          <p className="font-display text-3xl font-bold">{resumen.alertas}</p>
        </Card>
      </div>

      {alertas.length > 0 ? (
        <div className="flex flex-col gap-2">
          {alertas.map((a) => {
            const Icono = iconoAlerta[a.tipo]
            return (
              <Alert key={`${a.tipo}-${a.grupo_id}`} tone={a.tipo === 'ofrenda_con_diferencia' ? 'destructive' : 'warning'}>
                <span className="flex flex-wrap items-center justify-between gap-2">
                  <span className="flex items-center gap-2">
                    <Icono aria-hidden className="size-5" />
                    {textoAlerta(a, minimo)}
                  </span>
                  <Link className="underline" to={`/grupos/${a.grupo_id}`}>
                    Abrir grupo
                  </Link>
                </span>
              </Alert>
            )
          })}
        </div>
      ) : grupos.length > 0 ? (
        <Alert tone="success">Todo en orden: no hay avisos pendientes.</Alert>
      ) : null}

      {grupos.length > 0 ? (
        <Card>
          <ColumnsChart
            titulo="Asistencia por semana (todos tus grupos)"
            columnas={serie.map((s) => ({
              etiqueta: corta(s.semana),
              valor: s.pct,
              detalle: `${s.presentes} de ${s.registrados} presentes`,
            }))}
          />
        </Card>
      ) : null}

      <ul className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {grupos.map((g) => (
          <li key={g.id}>
            <Card className="flex h-full flex-col gap-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <CardTitle>
                    <Link className="underline" to={`/grupos/${g.id}`}>
                      {g.nombre}
                    </Link>
                  </CardTitle>
                  <CardDescription>
                    {g.integrantes} integrantes ·{' '}
                    {g.ultima_reunion
                      ? `última reunión ${corta(g.ultima_reunion)}`
                      : 'sin reuniones recientes'}
                  </CardDescription>
                </div>
                {g.sin_lista_esta_semana ? <Badge tone="warning">Sin lista esta semana</Badge> : null}
              </div>
              <Meter
                label="Asistencia reciente"
                value={g.asistencia_pct}
                tone={tonoAsistencia(g.asistencia_pct, minimo)}
              />
              <div className="flex flex-wrap gap-2">
                {g.peticiones_activas ? (
                  <Badge tone="primary">
                    {g.peticiones_activas === 1 ? '1 petición activa' : `${g.peticiones_activas} peticiones activas`}
                  </Badge>
                ) : null}
                {g.ofrendas ? (
                  <>
                    <Badge tone="neutral">Avalado en 30 días: {dinero(g.ofrendas.avalado_30_dias)}</Badge>
                    {g.ofrendas.pendientes ? (
                      <Badge tone="warning">{g.ofrendas.pendientes} por avalar</Badge>
                    ) : null}
                    {g.ofrendas.con_diferencia ? (
                      <Badge tone="destructive">{g.ofrendas.con_diferencia} con diferencia</Badge>
                    ) : null}
                  </>
                ) : null}
              </div>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  )
}

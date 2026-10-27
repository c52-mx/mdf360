import { useQuery } from '@tanstack/react-query'
import { CircleAlert, CircleCheck, TriangleAlert, type LucideIcon } from 'lucide-react'
import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardTitle,
  Field,
  PageHeader,
  SelectField,
  StackedChart,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'

type Nivel = 'info' | 'aviso' | 'error'

interface Evento {
  id: number
  fecha: string
  accion: string
  nivel: Nivel
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
interface Resumen {
  dias: { fecha: string; errores: number; avisos: number }[]
  modulos: string[]
}

/** Semáforo: verde informativo, amarillo aviso, rojo error. Siempre con ícono y texto. */
const semaforo: Record<Nivel, { tone: 'success' | 'warning' | 'destructive'; texto: string; icono: LucideIcon }> = {
  info: { tone: 'success', texto: 'Informativo', icono: CircleCheck },
  aviso: { tone: 'warning', texto: 'Aviso', icono: TriangleAlert },
  error: { tone: 'destructive', texto: 'Error', icono: CircleAlert },
}

const TAMANOS = ['25', '50', '100']
const corta = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })

export function AuditoriaPage() {
  const puede = useCan('bitacora.ver')
  const [modulo, setModulo] = useState('')
  const [nivel, setNivel] = useState('')
  const [q, setQ] = useState('')
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [tamano, setTamano] = useState('50')
  const [page, setPage] = useState(1)

  const resumen = useQuery({
    queryKey: ['auditoria-resumen'],
    enabled: puede,
    queryFn: () => api<Resumen>('/api/auditoria/resumen/?dias=14'),
  })
  const lista = useQuery({
    queryKey: ['auditoria', { modulo, nivel, q, desde, hasta, tamano, page }],
    enabled: puede,
    placeholderData: (previo) => previo,
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: tamano })
      if (modulo) params.set('action', modulo)
      if (nivel) params.set('nivel', nivel)
      if (q.trim()) params.set('q', q.trim())
      if (desde) params.set('desde', desde)
      if (hasta) params.set('hasta', hasta)
      return api<Pagina>(`/api/auditoria/?${params.toString()}`)
    },
  })

  if (!puede) return <Alert tone="warning">No tienes permiso para ver la bitácora.</Alert>

  const filtrar = (fn: () => void) => {
    fn()
    setPage(1)
  }
  const paginas = lista.data ? Math.max(1, Math.ceil(lista.data.count / Number(tamano))) : 1

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Bitácora"
        description="Registro de solo lectura de lo que ocurre en el sistema. Consultarla también queda registrado."
        module="admin"
      />

      {resumen.data ? (
        <Card>
          <StackedChart
            titulo="Errores y avisos por día (últimos 14 días)"
            series={[
              { nombre: 'Errores', tone: 'destructive' },
              { nombre: 'Avisos', tone: 'warning' },
            ]}
            columnas={resumen.data.dias.map((d) => ({
              etiqueta: corta(d.fecha),
              valores: [d.errores, d.avisos],
            }))}
          />
        </Card>
      ) : null}

      <Card className="flex flex-col gap-4">
        <CardTitle>Filtros</CardTitle>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <SelectField
            label="Tipo de evento"
            value={modulo}
            onChange={(e) => filtrar(() => setModulo(e.target.value))}
            options={[
              { value: '', label: 'Todos' },
              ...(resumen.data?.modulos ?? []).map((m) => ({ value: m, label: m })),
            ]}
          />
          <SelectField
            label="Nivel"
            value={nivel}
            onChange={(e) => filtrar(() => setNivel(e.target.value))}
            options={[
              { value: '', label: 'Todos' },
              { value: 'error', label: 'Errores (rojo)' },
              { value: 'aviso', label: 'Avisos (amarillo)' },
              { value: 'info', label: 'Informativos (verde)' },
            ]}
          />
          <Field
            label="Persona o número de objeto"
            value={q}
            onChange={(e) => filtrar(() => setQ(e.target.value))}
          />
          <Field label="Desde" type="date" value={desde} onChange={(e) => filtrar(() => setDesde(e.target.value))} />
          <Field label="Hasta" type="date" value={hasta} onChange={(e) => filtrar(() => setHasta(e.target.value))} />
          <SelectField
            label="Eventos por página"
            value={tamano}
            onChange={(e) => filtrar(() => setTamano(e.target.value))}
            options={TAMANOS.map((t) => ({ value: t, label: t }))}
          />
        </div>
      </Card>

      {lista.isError ? <Alert tone="destructive">{lista.error.message}</Alert> : null}
      {lista.data ? (
        <>
          <p className="text-muted-foreground">
            {lista.data.count === 1 ? '1 evento' : `${lista.data.count} eventos`}
          </p>
          {lista.data.results.length === 0 ? (
            <Alert>No hay eventos con esos filtros.</Alert>
          ) : (
            <Table aria-label="Eventos de la bitácora">
              <TableHead>
                <TableRow className="hover:bg-muted">
                  <TableHeaderCell>Nivel</TableHeaderCell>
                  <TableHeaderCell>Fecha</TableHeaderCell>
                  <TableHeaderCell>Evento</TableHeaderCell>
                  <TableHeaderCell>Quién</TableHeaderCell>
                  <TableHeaderCell>Sobre</TableHeaderCell>
                  <TableHeaderCell>Detalle</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {lista.data.results.map((e) => {
                  const { tone, texto, icono: Icono } = semaforo[e.nivel]
                  return (
                    <TableRow key={e.id}>
                      <TableCell>
                        <Badge tone={tone}>
                          <Icono aria-hidden className="size-4" />
                          {texto}
                        </Badge>
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {new Date(e.fecha).toLocaleString('es-MX')}
                      </TableCell>
                      <TableCell className="font-bold">{e.accion}</TableCell>
                      <TableCell>{e.actor || 'Sistema'}</TableCell>
                      <TableCell>{e.objeto || '–'}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {Object.keys(e.detalle).length > 0 ? JSON.stringify(e.detalle) : '–'}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
          <div className="flex items-center justify-between">
            <Button variant="outline" disabled={!lista.data.previous} onClick={() => setPage((n) => n - 1)}>
              Anterior
            </Button>
            <span className="text-muted-foreground">
              Página {page} de {paginas}
            </span>
            <Button variant="outline" disabled={!lista.data.next} onClick={() => setPage((n) => n + 1)}>
              Siguiente
            </Button>
          </div>
        </>
      ) : null}
    </div>
  )
}

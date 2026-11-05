import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  DataTable,
  Field,
  LineChart,
  Modal,
  PageHeader,
  SelectField,
  TableCell,
  TableRow,
  type DataColumn,
} from '@/design-system'
import { api } from '@/lib/api'
import { OfrendaIglesiaForm } from './ofrenda-iglesia-form'
import { AvalForm, dinero, estadoTone, type Ofrenda } from './ofrendas'
import { mesCorto, sinFiltros, type FilaResumen, type Filtros, type Resumen, type TiposRespuesta } from './ofrendas-types'
import { TiposOfrenda } from './tipos-ofrenda'
import { fechaLarga } from './types'

const ORIGENES = [
  { value: '', label: 'Grupos e iglesia' },
  { value: 'grupo', label: 'Solo grupos' },
  { value: 'iglesia', label: 'Solo iglesia' },
]
const ESTADOS = [
  { value: '', label: 'Todos' },
  { value: 'pendiente', label: 'Pendiente de aval' },
  { value: 'avalada', label: 'Avalada' },
  { value: 'diferencia', label: 'Con diferencia' },
]

function consulta(f: Filtros) {
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(f)) if (v) p.set(k, v)
  return p.toString()
}

function Total({ titulo, valor, nota }: { titulo: string; valor: string; nota?: string }) {
  return (
    <Card className="flex flex-col gap-1">
      <CardDescription>{titulo}</CardDescription>
      <span className="font-display text-2xl font-bold">{dinero(valor)}</span>
      {nota ? <CardDescription>{nota}</CardDescription> : null}
    </Card>
  )
}

/**
 * Ofrendas como finanzas: filtros dinámicos, totales, gráfica en el tiempo, tabla de movimientos
 * y, para quien avala, lo que está por contar. Cada quien ve solo lo que le corresponde.
 */
export function OfrendasPage() {
  const queryClient = useQueryClient()
  const [filtros, setFiltros] = useState<Filtros>(sinFiltros)
  const [capturando, setCapturando] = useState(false)
  const [avalando, setAvalando] = useState<Ofrenda | null>(null)

  const resumen = useQuery({
    queryKey: ['ofrendas', 'resumen', filtros],
    queryFn: () => api<Resumen>(`/api/grupos/ofrendas/resumen/?${consulta(filtros)}`),
  })
  const tipos = useQuery({
    queryKey: ['ofrendas-tipos', 'todos'],
    queryFn: () => api<TiposRespuesta>('/api/grupos/ofrendas/tipos/'),
  })
  const iglesia = useQuery({
    queryKey: ['ofrendas', 'iglesia'],
    queryFn: () => api<{ puede_capturar: boolean }>('/api/grupos/ofrendas/iglesia/'),
  })
  const pendientes = useQuery({
    queryKey: ['ofrendas-pendientes'],
    queryFn: () => api<Ofrenda[]>('/api/grupos/ofrendas/pendientes/'),
  })

  const cambiar = (campo: keyof Filtros) => (valor: string) => setFiltros((f) => ({ ...f, [campo]: valor }))
  const datos = resumen.data
  const hayFiltros = Object.values(filtros).some(Boolean)

  const columnas: DataColumn<FilaResumen>[] = [
    {
      clave: 'fecha',
      titulo: 'Fecha',
      orden: (o) => o.fecha,
      celda: (o) => new Date(`${o.fecha}T12:00:00`).toLocaleDateString('es-MX'),
    },
    { clave: 'origen', titulo: 'De dónde viene', orden: (o) => o.origen_display, celda: (o) => o.origen_display },
    {
      clave: 'tipo',
      titulo: 'Tipo',
      orden: (o) => o.tipo,
      celda: (o) => (o.concepto ? `${o.tipo} · ${o.concepto}` : o.tipo),
    },
    { clave: 'monto', titulo: 'Monto', numerica: true, orden: (o) => Number(o.monto), celda: (o) => dinero(o.monto) },
    {
      clave: 'estado',
      titulo: 'Estado',
      orden: (o) => o.estado_display,
      celda: (o) => <Badge tone={estadoTone[o.estado]}>{o.estado_display}</Badge>,
    },
  ]

  const columnasPendientes: DataColumn<Ofrenda>[] = [
    { clave: 'fecha', titulo: 'Fecha', orden: (o) => o.fecha, celda: (o) => fechaLarga(o.fecha) },
    { clave: 'origen', titulo: 'De dónde viene', orden: (o) => o.grupo, celda: (o) => o.grupo },
    {
      clave: 'tipo',
      titulo: 'Tipo',
      orden: (o) => o.tipo_display,
      celda: (o) => (o.concepto ? `${o.tipo_display} · ${o.concepto}` : o.tipo_display),
    },
    { clave: 'monto', titulo: 'Capturado', numerica: true, orden: (o) => Number(o.monto), celda: (o) => dinero(o.monto) },
    {
      clave: 'estado',
      titulo: 'Estado',
      orden: (o) => o.estado_display,
      celda: (o) => <Badge tone={estadoTone[o.estado]}>{o.estado_display}</Badge>,
    },
    {
      clave: 'acciones',
      titulo: 'Acciones',
      celda: (o) => (
        <Button size="sm" onClick={() => setAvalando(o)}>
          Contar y avalar
        </Button>
      ),
    },
  ]

  const opcionesTipo = [
    { value: '', label: 'Todos' },
    ...(tipos.data?.tipos ?? []).map((t) => ({ value: String(t.id), label: t.nombre })),
  ]

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Ofrendas"
        description="Totales y movimientos de lo que tienes permiso de ver."
        module="grupos"
        actions={
          iglesia.data?.puede_capturar ? (
            <Button onClick={() => setCapturando(true)}>Capturar ofrenda de la iglesia</Button>
          ) : null
        }
      />
      {resumen.isError ? <Alert tone="destructive">{resumen.error.message}</Alert> : null}

      {pendientes.data && pendientes.data.length > 0 ? (
        <Card className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <CardTitle>Por avalar</CardTitle>
            <CardDescription>Cuenta la ofrenda, escribe tu cifra y confirma con tu PIN.</CardDescription>
          </div>
          {pendientes.data.some((o) => o.estado === 'diferencia') ? (
            <Alert tone="destructive">Hay ofrendas con diferencia. Revisa la cifra capturada y la contada.</Alert>
          ) : null}
          <DataTable
            titulo="Ofrendas por avalar"
            columnas={columnasPendientes}
            filas={pendientes.data}
            clave={(o) => `${o.origen ?? 'grupo'}:${o.id}`}
            ordenInicial={{ clave: 'fecha', descendente: true }}
          />
        </Card>
      ) : null}

      <Card className="flex flex-col gap-3">
        <CardTitle>Filtros</CardTitle>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Field label="Desde" type="date" value={filtros.desde} onChange={(e) => cambiar('desde')(e.target.value)} />
          <Field label="Hasta" type="date" value={filtros.hasta} onChange={(e) => cambiar('hasta')(e.target.value)} />
          <SelectField label="Origen" options={ORIGENES} value={filtros.origen} onChange={(e) => cambiar('origen')(e.target.value)} />
          <SelectField label="Tipo" options={opcionesTipo} value={filtros.tipo} onChange={(e) => cambiar('tipo')(e.target.value)} />
          <SelectField label="Estado" options={ESTADOS} value={filtros.estado} onChange={(e) => cambiar('estado')(e.target.value)} />
        </div>
        {hayFiltros ? (
          <div>
            <Button variant="ghost" onClick={() => setFiltros(sinFiltros)}>
              Quitar filtros
            </Button>
          </div>
        ) : null}
      </Card>

      {datos ? (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Total titulo="Total" valor={datos.totales.total} nota={`${datos.totales.cantidad} movimientos`} />
            <Total titulo="Avalado" valor={datos.totales.avalado} />
            <Total titulo="Por avalar" valor={datos.totales.por_avalar} />
            <Total titulo="Grupos / Iglesia" valor={datos.totales.grupo} nota={`Iglesia: ${dinero(datos.totales.iglesia)}`} />
          </div>

          <Card className="flex flex-col gap-3">
            <CardTitle>Ofrendas por mes</CardTitle>
            <LineChart
              titulo="Ofrendas recibidas por mes"
              formato={(v) => dinero(v)}
              series={[
                { nombre: 'Grupos', puntos: datos.por_mes.map((m) => ({ etiqueta: mesCorto(m.mes), valor: Number(m.grupo) })) },
                { nombre: 'Iglesia', puntos: datos.por_mes.map((m) => ({ etiqueta: mesCorto(m.mes), valor: Number(m.iglesia) })) },
              ]}
            />
          </Card>

          <Card className="flex flex-col gap-3">
            <CardTitle>Por tipo de ofrenda</CardTitle>
            <DataTable
              titulo="Total por tipo"
              columnas={[
                { clave: 'tipo', titulo: 'Tipo', orden: (t) => t.tipo, celda: (t) => t.tipo },
                { clave: 'monto', titulo: 'Total', numerica: true, orden: (t) => Number(t.monto), celda: (t) => dinero(t.monto) },
                {
                  clave: 'parte',
                  titulo: '% del total',
                  numerica: true,
                  orden: (t) => Number(t.monto),
                  celda: (t) =>
                    Number(datos.totales.total) > 0
                      ? `${Math.round((Number(t.monto) / Number(datos.totales.total)) * 100)}%`
                      : '–',
                },
              ]}
              filas={datos.por_tipo}
              clave={(t) => t.tipo}
              ordenInicial={{ clave: 'monto', descendente: true }}
              vacio="Sin movimientos con estos filtros."
            />
          </Card>

          <Card className="flex flex-col gap-3">
            <CardTitle>Movimientos</CardTitle>
            {datos.truncado ? (
              <Alert tone="warning">Hay demasiados movimientos: acota las fechas para ver todos.</Alert>
            ) : null}
            <DataTable
              titulo="Movimientos de ofrendas"
              columnas={columnas}
              filas={datos.filas}
              clave={(o) => `${o.origen}:${o.id}`}
              ordenInicial={{ clave: 'fecha', descendente: true }}
              vacio="Sin movimientos con estos filtros."
              pie={
                <TableRow>
                  <TableCell>Total</TableCell>
                  <TableCell>{datos.totales.cantidad} movimientos</TableCell>
                  <TableCell />
                  <TableCell className="text-right">{dinero(datos.totales.total)}</TableCell>
                  <TableCell />
                </TableRow>
              }
            />
          </Card>
        </>
      ) : null}

      <TiposOfrenda />

      <OfrendaIglesiaForm abierto={capturando} onCerrar={() => setCapturando(false)} />
      <Modal
        open={avalando !== null}
        onClose={() => setAvalando(null)}
        title="Contar y avalar"
        description={avalando ? `${avalando.grupo} · ${dinero(avalando.monto)} capturados` : undefined}
      >
        {avalando ? (
          <AvalForm
            ofrenda={avalando}
            onListo={() => {
              setAvalando(null)
              void queryClient.invalidateQueries({ queryKey: ['ofrendas-pendientes'] })
              void queryClient.invalidateQueries({ queryKey: ['ofrendas'] })
            }}
          />
        ) : null}
      </Modal>
    </div>
  )
}

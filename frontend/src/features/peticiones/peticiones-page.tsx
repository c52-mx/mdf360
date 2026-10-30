import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  Collapsible,
  DataTable,
  LineChart,
  Modal,
  PageHeader,
  type DataColumn,
} from '@/design-system'
import { useAuth, useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'
import { etiquetasDe, PeticionesPanel, PeticionItem, useFormularioPeticiones } from './peticiones-panel'
import type { Pagina, Peticion } from './types'

interface Resumen {
  semanas: { semana: string; activas: number; atendidas: number }[]
  totales: { activas: number; atendidas: number }
  dias_retencion: number
}

const TOPE = 100

/** Primer texto de la petición, para reconocerla en la tabla sin abrirla. */
function extracto(p: Peticion): string {
  if (p.ilegible) return 'No se puede leer'
  if (!p.datos) return '–'
  const texto = (p.datos.peticion ?? Object.values(p.datos).find((v) => typeof v === 'string' && v)) as
    | string
    | undefined
  if (!texto) return '–'
  return texto.length > 90 ? `${texto.slice(0, 90)}…` : texto
}

const semanaCorta = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })

/**
 * Todas las peticiones que la persona puede ver, agrupadas por canal de llegada (grupo o persona),
 * dentro de cada uno por estado, y por fecha. Cada una indica siempre de dónde viene.
 */
export function PeticionesPage() {
  const queryClient = useQueryClient()
  const puedeConfigurar = useCan('peticiones.configurar')
  const { user } = useAuth()
  const [abierta, setAbierta] = useState<Peticion | null>(null)

  const resumen = useQuery({
    queryKey: ['peticiones', 'resumen'],
    queryFn: () => api<Resumen>('/api/peticiones/resumen/'),
  })
  const formulario = useFormularioPeticiones()
  const lista = useQuery({
    queryKey: ['peticiones', 'todas'],
    queryFn: () => api<Pagina<Peticion>>(`/api/peticiones/?page_size=${TOPE}`),
  })
  const cambiar = useMutation({
    mutationFn: ({ id, estado: nuevo }: { id: number; estado: 'activa' | 'atendida' }) =>
      api<Peticion>(`/api/peticiones/${id}/`, { method: 'PATCH', body: { estado: nuevo } }),
    onSuccess: (actualizada) => {
      setAbierta((actual) => (actual?.id === actualizada.id ? actualizada : actual))
      void queryClient.invalidateQueries({ queryKey: ['peticiones'] })
    },
  })
  const etiquetas = etiquetasDe(formulario.data)

  // Canal de llegada -> peticiones, ya ordenadas por fecha (la más reciente primero)
  const canales = useMemo(() => {
    const mapa = new Map<string, { nombre: string; filas: Peticion[] }>()
    for (const p of lista.data?.results ?? []) {
      const canal = mapa.get(p.origen.tipo) ?? { nombre: p.origen.tipo_display, filas: [] }
      canal.filas.push(p)
      mapa.set(p.origen.tipo, canal)
    }
    return [...mapa.entries()].map(([tipo, c]) => ({ tipo, ...c }))
  }, [lista.data])

  const columnas = (): DataColumn<Peticion>[] => [
    {
      clave: 'fecha',
      titulo: 'Fecha',
      orden: (p) => p.creada_en,
      celda: (p) => new Date(p.creada_en).toLocaleDateString('es-MX'),
    },
    {
      clave: 'origen',
      titulo: 'De dónde',
      orden: (p) => p.origen.etiqueta,
      celda: (p) => p.origen.etiqueta,
    },
    { clave: 'texto', titulo: 'Petición', celda: (p) => extracto(p) },
    {
      clave: 'alcance',
      titulo: 'Quién la ve',
      orden: (p) => p.visibilidad_display,
      celda: (p) => <Badge tone="neutral">{p.visibilidad_display}</Badge>,
    },
    {
      clave: 'acciones',
      titulo: 'Acciones',
      celda: (p) => (
        <span className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => setAbierta(p)}>
            Ver
          </Button>
          {p.puede_gestionar ? (
            <Button
              size="sm"
              variant="ghost"
              disabled={cambiar.isPending}
              onClick={() => cambiar.mutate({ id: p.id, estado: p.estado === 'activa' ? 'atendida' : 'activa' })}
            >
              {p.estado === 'activa' ? 'Marcar atendida' : 'Reactivar'}
            </Button>
          ) : null}
        </span>
      ),
    },
  ]

  const semanas = resumen.data?.semanas ?? []

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

      <Card className="flex flex-col gap-3">
        <CardTitle>Atendidas y pendientes</CardTitle>
        <LineChart
          titulo="Peticiones recibidas por semana"
          series={[
            {
              nombre: 'Atendidas',
              puntos: semanas.map((s) => ({ etiqueta: semanaCorta(s.semana), valor: s.atendidas })),
            },
            {
              nombre: 'Pendientes',
              puntos: semanas.map((s) => ({ etiqueta: semanaCorta(s.semana), valor: s.activas })),
            },
          ]}
        />
        {resumen.data ? (
          <CardDescription>
            {resumen.data.totales.atendidas} atendidas y {resumen.data.totales.activas} pendientes. Solo se
            cuentan las que puedes ver, y cada una se borra a los {resumen.data.dias_retencion} días.
          </CardDescription>
        ) : null}
        {resumen.isError ? <Alert tone="destructive">{resumen.error.message}</Alert> : null}
      </Card>

      {user ? (
        <Collapsible title="Pedir oración" summary="Tu petición personal; la ven solo quienes tú permitas.">
          <PeticionesPanel
            origenTipo="persona"
            origenId={user.id}
            puedeRegistrar
            titulo="Pedir oración"
            alcances={['lideres', 'equipo']}
          />
        </Collapsible>
      ) : null}

      {lista.isError ? <Alert tone="destructive">{lista.error.message}</Alert> : null}
      {cambiar.error ? <Alert tone="destructive">{cambiar.error.message}</Alert> : null}
      {lista.data && lista.data.results.length === 0 ? <Alert>Aún no hay peticiones para mostrar.</Alert> : null}
      {lista.data?.next ? (
        <Alert tone="warning">
          Hay más de {TOPE} peticiones: aquí se muestran las {TOPE} más recientes.
        </Alert>
      ) : null}

      {canales.map((canal) => {
        const activas = canal.filas.filter((p) => p.estado === 'activa')
        const atendidas = canal.filas.filter((p) => p.estado === 'atendida')
        return (
          <Collapsible
            key={canal.tipo}
            title={canal.nombre}
            summary={`${activas.length} pendientes · ${atendidas.length} atendidas`}
            defaultOpen={canales.length === 1}
          >
            <div className="flex flex-col gap-5">
              {[
                { clave: 'activas', titulo: 'Pendientes', filas: activas },
                { clave: 'atendidas', titulo: 'Atendidas', filas: atendidas },
              ].map((grupo) => (
                <section key={grupo.clave} className="flex flex-col gap-2">
                  <h3 className="text-lg">
                    {grupo.titulo} ({grupo.filas.length})
                  </h3>
                  <DataTable
                    titulo={`${canal.nombre}: ${grupo.titulo.toLowerCase()}`}
                    columnas={columnas()}
                    filas={grupo.filas}
                    clave={(p) => p.id}
                    ordenInicial={{ clave: 'fecha', descendente: true }}
                    vacio={`No hay peticiones ${grupo.titulo.toLowerCase()}.`}
                  />
                </section>
              ))}
            </div>
          </Collapsible>
        )
      })}

      <Modal open={abierta !== null} onClose={() => setAbierta(null)} title="Petición de oración">
        {abierta ? (
          <PeticionItem
            p={abierta}
            etiquetas={etiquetas}
            onEstado={(id, nuevo) => cambiar.mutate({ id, estado: nuevo })}
          />
        ) : null}
      </Modal>
    </div>
  )
}

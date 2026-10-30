import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  DataTable,
  PageHeader,
  type DataColumn,
} from '@/design-system'
import { api } from '@/lib/api'
import { EnviarAvisoCard } from './enviar-aviso-card'
import { TableroPanel } from './tablero-panel'

/** Cómo se ordenan los tableros recibidos. */
const ORDEN_TIPO = ['persona', 'iglesia', 'grupo', 'unidad']

interface Tablero {
  tipo: string
  tipo_display: string
  id: number
  etiqueta: string
  no_leidos: number
  puede_publicar: boolean
}

interface AvisoPendiente {
  id: number
  texto: string
  autor: string
  creado_en: string
  estado: 'pendiente' | 'rechazado' | 'publicado'
  estado_display: string
  puede_resolver: boolean
}
interface PorAutorizar {
  puede_autorizar: boolean
  avisos: AvisoPendiente[]
}

const clave = (t: Tablero) => `${t.tipo}:${t.id}`

/** Los tableros de mensajes de todos los lugares donde la persona participa. */
export function AvisosPage() {
  const queryClient = useQueryClient()
  const [abierto, setAbierto] = useState<string | null>(null)
  const tableros = useQuery({
    queryKey: ['tablero-no-leidos', 'mis-tableros'],
    queryFn: () => api<Tablero[]>('/api/tablero/mis-tableros/'),
  })
  const porAutorizar = useQuery({
    queryKey: ['tablero-por-autorizar'],
    queryFn: () => api<PorAutorizar>('/api/tablero/por-autorizar/'),
    refetchInterval: 30_000,
  })
  const resolver = useMutation({
    mutationFn: ({ id, autorizar }: { id: number; autorizar: boolean }) =>
      api(`/api/tablero/${id}/${autorizar ? 'autorizar' : 'rechazar'}/`, { method: 'POST', body: {} }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['tablero-por-autorizar'] })
      void queryClient.invalidateQueries({ queryKey: ['tablero-no-leidos'] })
    },
  })

  const filas = [...(tableros.data ?? [])].sort(
    (a, b) => ORDEN_TIPO.indexOf(a.tipo) - ORDEN_TIPO.indexOf(b.tipo) || a.etiqueta.localeCompare(b.etiqueta, 'es'),
  )
  const activo = filas.find((t) => clave(t) === abierto)

  const columnas: DataColumn<Tablero>[] = [
    {
      clave: 'lugar',
      titulo: 'Lugar',
      orden: (t) => t.etiqueta,
      celda: (t) => <span className="font-bold">{t.etiqueta}</span>,
    },
    { clave: 'tipo', titulo: 'Tipo', orden: (t) => t.tipo_display, celda: (t) => t.tipo_display },
    {
      clave: 'nuevos',
      titulo: 'Nuevos',
      numerica: true,
      orden: (t) => t.no_leidos,
      celda: (t) =>
        t.no_leidos > 0 ? (
          <Badge tone="destructive">{t.no_leidos === 1 ? '1 mensaje nuevo' : `${t.no_leidos} mensajes nuevos`}</Badge>
        ) : (
          '–'
        ),
    },
    {
      clave: 'abrir',
      titulo: 'Acciones',
      celda: (t) => (
        <Button size="sm" onClick={() => setAbierto(clave(t))}>
          Abrir
        </Button>
      ),
    },
  ]

  const columnasPendientes: DataColumn<AvisoPendiente>[] = [
    {
      clave: 'fecha',
      titulo: 'Fecha',
      orden: (a) => a.creado_en,
      celda: (a) => new Date(a.creado_en).toLocaleDateString('es-MX'),
    },
    { clave: 'autor', titulo: 'Quién lo pide', orden: (a) => a.autor, celda: (a) => a.autor },
    { clave: 'texto', titulo: 'Aviso', celda: (a) => <span className="whitespace-pre-line">{a.texto}</span> },
    {
      clave: 'estado',
      titulo: 'Estado',
      orden: (a) => a.estado_display,
      celda: (a) => (
        <Badge tone={a.estado === 'rechazado' ? 'destructive' : 'warning'}>{a.estado_display}</Badge>
      ),
    },
    {
      clave: 'acciones',
      titulo: 'Acciones',
      celda: (a) =>
        a.puede_resolver && a.estado === 'pendiente' ? (
          <span className="flex flex-wrap gap-2">
            <Button
              size="sm"
              disabled={resolver.isPending}
              onClick={() => resolver.mutate({ id: a.id, autorizar: true })}
            >
              Autorizar
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={resolver.isPending}
              onClick={() => resolver.mutate({ id: a.id, autorizar: false })}
            >
              Rechazar
            </Button>
          </span>
        ) : null,
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Avisos"
        description="Mensajes de la iglesia, de tus grupos y de tus ministerios."
        module="grupos"
        actions={<EnviarAvisoCard />}
      />
      {tableros.isError ? <Alert tone="destructive">{tableros.error.message}</Alert> : null}
      {resolver.error ? <Alert tone="destructive">{resolver.error.message}</Alert> : null}

      {porAutorizar.data && porAutorizar.data.avisos.length > 0 ? (
        <Card className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <CardTitle>Avisos por autorizar</CardTitle>
            <CardDescription>
              {porAutorizar.data.puede_autorizar
                ? 'Avisos a toda la iglesia que esperan tu autorización. Nadie autoriza su propio aviso.'
                : 'Tus avisos a toda la iglesia: salen cuando alguien los autoriza.'}
            </CardDescription>
          </div>
          <DataTable
            titulo="Avisos por autorizar"
            columnas={columnasPendientes}
            filas={porAutorizar.data.avisos}
            clave={(a) => a.id}
            ordenInicial={{ clave: 'fecha', descendente: true }}
          />
        </Card>
      ) : null}

      {activo ? (
        <div className="flex flex-col gap-3">
          <Button variant="ghost" onClick={() => setAbierto(null)}>
            Cerrar {activo.etiqueta}
          </Button>
          <TableroPanel
            origenTipo={activo.tipo}
            origenId={activo.id}
            puedePublicar={activo.puede_publicar}
            titulo={activo.etiqueta}
          />
        </div>
      ) : null}

      <DataTable
        titulo="Tus tableros de avisos"
        columnas={columnas}
        filas={filas}
        clave={clave}
        vacio="Todavía no participas en ningún tablero."
      />
    </div>
  )
}

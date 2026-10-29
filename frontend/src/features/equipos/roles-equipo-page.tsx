import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  CheckboxField,
  ConfirmButton,
  Field,
  PageHeader,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
  useToast,
} from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'
import type { AmbitoEquipo, RolEquipo } from './use-roles-equipo'

interface AccionEquipo {
  codigo: string
  accion: string
  pantalla: string
  sensible: boolean
}

interface Borrador {
  nombre: string
  descripcion: string
  permisos: string[]
}

const AMBITOS: { valor: AmbitoEquipo; titulo: string; ayuda: string }[] = [
  {
    valor: 'ministerio',
    titulo: 'Ministerios',
    ayuda: 'Cada ministerio lleva un encargado, una persona de respaldo y servidores.',
  },
  {
    valor: 'grupo',
    titulo: 'Grupos de Conexión',
    ayuda: 'Cada grupo lleva un líder, una persona de respaldo y servidores, entre otros roles.',
  },
]

/** Roles dentro de un grupo o ministerio: se elige qué puede hacer quien tiene cada uno. */
export function RolesEquipoPage() {
  const puede = useCan('roles.administrar')
  const queryClient = useQueryClient()
  const toast = useToast()
  const [ambito, setAmbito] = useState<AmbitoEquipo>('ministerio')
  const [clave, setClave] = useState<string | 'nuevo' | null>(null)
  const [borrador, setBorrador] = useState<Borrador | null>(null)

  const roles = useQuery({
    queryKey: ['roles-equipo', ambito, 'todos'],
    enabled: puede,
    queryFn: () => api<RolEquipo[]>(`/api/auth/roles-equipo/?ambito=${ambito}&todos=1`),
  })
  const catalogo = useQuery({
    queryKey: ['permisos-equipo', ambito],
    enabled: puede,
    queryFn: () => api<AccionEquipo[]>(`/api/auth/permisos-equipo/${ambito}/`),
    staleTime: 60_000,
  })

  const refrescar = () => void queryClient.invalidateQueries({ queryKey: ['roles-equipo'] })
  const volver = () => {
    setClave(null)
    setBorrador(null)
  }

  const guardar = useMutation({
    mutationFn: () =>
      clave === 'nuevo'
        ? api<RolEquipo>('/api/auth/roles-equipo/', { method: 'POST', body: { ...borrador, ambito } })
        : api<RolEquipo>(`/api/auth/roles-equipo/${ambito}/${clave}/`, { method: 'PATCH', body: borrador }),
    onSuccess: (rol) => {
      toast.mostrar(`El rol «${rol.nombre}» se guardó.`)
      refrescar()
      volver()
    },
  })
  const cambiarEstado = useMutation({
    mutationFn: ({ rol, activo }: { rol: RolEquipo; activo: boolean }) =>
      api<RolEquipo>(`/api/auth/roles-equipo/${rol.ambito}/${rol.clave}/`, {
        method: 'PATCH',
        body: { activo },
      }),
    onSuccess: (rol) => {
      toast.mostrar(rol.activo ? `«${rol.nombre}» volvió a estar activo.` : `«${rol.nombre}» se desactivó.`)
      refrescar()
      volver()
    },
  })

  if (!puede) return <Alert tone="warning">No tienes permiso para administrar roles.</Alert>

  const lista = roles.data ?? []
  const error = guardar.error ?? cambiarEstado.error ?? roles.error ?? catalogo.error
  const info = AMBITOS.find((a) => a.valor === ambito)!

  if (clave !== null && borrador !== null) {
    const actual = lista.find((r) => r.clave === clave)
    const marcados = new Set(borrador.permisos)
    const alternar = (codigo: string, activo: boolean) =>
      setBorrador({
        ...borrador,
        permisos: activo ? [...borrador.permisos, codigo] : borrador.permisos.filter((p) => p !== codigo),
      })
    const pantallas = [...new Set((catalogo.data ?? []).map((a) => a.pantalla))]

    return (
      <div className="flex flex-col gap-6">
        <button
          type="button"
          onClick={() => {
            guardar.reset()
            volver()
          }}
          className="presionable flex w-fit items-center gap-2 font-semibold text-primary"
        >
          <ArrowLeft aria-hidden className="size-5" />
          Volver al listado
        </button>
        <PageHeader
          title={clave === 'nuevo' ? 'Nuevo rol' : borrador.nombre}
          description={`${info.titulo}: elige lo que puede hacer quien tenga este rol.`}
          module="admin"
        />
        {error ? <Alert tone="destructive">{error.message}</Alert> : null}
        <Card className="grid max-w-3xl grid-cols-1 gap-4">
          <Field
            label="Nombre"
            value={borrador.nombre}
            onChange={(e) => setBorrador({ ...borrador, nombre: e.target.value })}
          />
          <Field
            label="Descripción"
            value={borrador.descripcion}
            onChange={(e) => setBorrador({ ...borrador, descripcion: e.target.value })}
          />
        </Card>
        <Card className="flex flex-col gap-4">
          <CardTitle>Lo que puede hacer</CardTitle>
          {pantallas.map((pantalla) => (
            <fieldset key={pantalla} className="flex flex-col gap-1">
              <legend className="font-bold">{pantalla}</legend>
              {catalogo.data
                ?.filter((a) => a.pantalla === pantalla)
                .map((a) => (
                  <div key={a.codigo} className="flex flex-wrap items-center gap-x-3">
                    <CheckboxField
                      label={a.accion}
                      checked={marcados.has(a.codigo)}
                      onChange={(e) => alternar(a.codigo, e.target.checked)}
                    />
                    {a.sensible ? <Badge tone="warning">Sensible</Badge> : null}
                  </div>
                ))}
            </fieldset>
          ))}
          <CardDescription>
            Quien tenga un rol que agrega o cambia integrantes, o que ve el historial, solo puede ser
            asignado por la administración.
          </CardDescription>
        </Card>
        <div className="flex flex-wrap items-center gap-3">
          <Button onClick={() => guardar.mutate()} disabled={guardar.isPending || !borrador.nombre.trim()}>
            Guardar rol
          </Button>
          {actual && !actual.es_base && actual.activo ? (
            <ConfirmButton
              variant="outline"
              pregunta="¿Desactivar este rol?"
              etiquetaConfirmar="Sí, desactivar"
              onConfirm={() => cambiarEstado.mutate({ rol: actual, activo: false })}
            >
              Desactivar
            </ConfirmButton>
          ) : null}
          {actual && !actual.activo ? (
            <Button variant="success" onClick={() => cambiarEstado.mutate({ rol: actual, activo: true })}>
              Activar
            </Button>
          ) : null}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <Link to="/permisos" className="presionable flex w-fit items-center gap-2 font-semibold text-primary">
        <ArrowLeft aria-hidden className="size-5" />
        Volver a roles y permisos
      </Link>
      <PageHeader
        title="Roles de grupos y ministerios"
        description="Define qué puede hacer quien tiene cada rol dentro de un grupo o de un ministerio."
        module="admin"
        actions={
          <Button
            onClick={() => {
              setClave('nuevo')
              setBorrador({ nombre: '', descripcion: '', permisos: [] })
            }}
          >
            <Plus aria-hidden className="size-5" />
            Nuevo rol
          </Button>
        }
      />
      <div role="group" aria-label="Ámbito" className="flex flex-wrap gap-2">
        {AMBITOS.map((a) => (
          <Button
            key={a.valor}
            variant={a.valor === ambito ? 'primary' : 'outline'}
            aria-pressed={a.valor === ambito}
            onClick={() => setAmbito(a.valor)}
          >
            {a.titulo}
          </Button>
        ))}
      </div>
      <CardDescription>
        {info.ayuda} Los roles son independientes: ser encargado de un ministerio no da acceso a un
        grupo, ni al revés.
      </CardDescription>
      {error ? <Alert tone="destructive">{error.message}</Alert> : null}
      <Table aria-label={`Roles de ${info.titulo}`}>
        <TableHead>
          <TableRow className="hover:bg-muted">
            <TableHeaderCell>Rol</TableHeaderCell>
            <TableHeaderCell>Personas</TableHeaderCell>
            <TableHeaderCell>Acciones permitidas</TableHeaderCell>
            <TableHeaderCell>
              <span className="sr-only">Abrir</span>
            </TableHeaderCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {lista.map((r) => (
            <TableRow key={r.clave}>
              <TableCell>
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-bold">{r.nombre}</span>
                  {r.es_base ? <Badge>Base</Badge> : null}
                  {!r.activo ? <Badge tone="warning">Desactivado</Badge> : null}
                </span>
                {r.descripcion ? <span className="text-sm text-muted-foreground">{r.descripcion}</span> : null}
              </TableCell>
              <TableCell>{r.en_uso}</TableCell>
              <TableCell>{r.permisos.length}</TableCell>
              <TableCell>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setClave(r.clave)
                    setBorrador({ nombre: r.nombre, descripcion: r.descripcion, permisos: r.permisos })
                  }}
                >
                  Editar
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

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
import { api } from '@/lib/api'
import { useAuth, useCan } from './use-auth'

export interface RolCompleto {
  clave: string
  nombre: string
  descripcion: string
  nivel: number
  permisos: string[]
  exige_credencial_fuerte: boolean
  activo: boolean
  es_base: boolean
  editable: boolean
  usuarios: number
}

export interface Catalogo {
  modulo: string
  pantallas: {
    pantalla: string
    acciones: { codigo: string; accion: string; sensible: boolean }[]
  }[]
}

interface Borrador {
  nombre: string
  descripcion: string
  nivel: number
  exige_credencial_fuerte: boolean
  permisos: string[]
}

const vacio = (nivel: number): Borrador => ({
  nombre: '',
  descripcion: '',
  nivel,
  exige_credencial_fuerte: false,
  permisos: [],
})

/** Roles y permisos: se crea un rol y se marcan las acciones que puede hacer, por módulo y pantalla. */
export function PermisosPage() {
  const puede = useCan('roles.administrar')
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [clave, setClave] = useState<string | 'nuevo' | null>(null)
  const [borrador, setBorrador] = useState<Borrador | null>(null)

  const roles = useQuery({
    queryKey: ['roles', 'todos'],
    enabled: puede,
    queryFn: () => api<RolCompleto[]>('/api/auth/roles/?todos=1'),
  })
  const catalogo = useQuery({
    queryKey: ['catalogo-permisos'],
    enabled: puede,
    queryFn: () => api<Catalogo[]>('/api/auth/permisos/'),
    staleTime: 60_000,
  })

  const refrescar = () => {
    void queryClient.invalidateQueries({ queryKey: ['roles'] })
    void queryClient.invalidateQueries({ queryKey: ['usuarios'] })
  }
  const volver = () => {
    setClave(null)
    setBorrador(null)
  }

  const guardar = useMutation({
    mutationFn: () =>
      clave === 'nuevo'
        ? api<RolCompleto>('/api/auth/roles/', { method: 'POST', body: borrador })
        : api<RolCompleto>(`/api/auth/roles/${clave}/`, { method: 'PATCH', body: borrador }),
    onSuccess: (rol) => {
      toast.mostrar(`El rol «${rol.nombre}» se guardó.`)
      refrescar()
      volver()
    },
  })
  const duplicar = useMutation({
    mutationFn: (rolClave: string) =>
      api<RolCompleto>(`/api/auth/roles/${rolClave}/duplicar/`, { method: 'POST', body: {} }),
    onSuccess: (copia) => {
      toast.mostrar(`Se creó «${copia.nombre}». Ajusta su nombre y sus permisos.`)
      refrescar()
      setClave(copia.clave)
      setBorrador({ ...copia })
    },
  })
  const cambiarEstado = useMutation({
    mutationFn: ({ rolClave, activar }: { rolClave: string; activar: boolean }) =>
      api<RolCompleto>(`/api/auth/roles/${rolClave}/${activar ? 'activar' : 'desactivar'}/`, {
        method: 'POST',
        body: {},
      }),
    onSuccess: (rol) => {
      toast.mostrar(rol.activo ? `«${rol.nombre}» volvió a estar activo.` : `«${rol.nombre}» se desactivó.`)
      refrescar()
      volver()
    },
  })

  if (!puede) return <Alert tone="warning">No tienes permiso para administrar roles.</Alert>

  const lista = roles.data ?? []
  // Mi nivel es el más alto (número menor) entre mis roles
  const miNivel = Math.min(99, ...lista.filter((r) => user?.roles.includes(r.clave)).map((r) => r.nivel))
  const mios = new Set(user?.permisos ?? [])
  const error = guardar.error ?? duplicar.error ?? cambiarEstado.error ?? roles.error ?? catalogo.error

  if (clave !== null && borrador !== null) {
    const actual = lista.find((r) => r.clave === clave)
    const editable = clave === 'nuevo' || !!actual?.editable
    const marcados = new Set(borrador.permisos)
    const alternar = (codigo: string, activo: boolean) =>
      setBorrador({
        ...borrador,
        permisos: activo ? [...borrador.permisos, codigo] : borrador.permisos.filter((p) => p !== codigo),
      })

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
          description={
            clave === 'nuevo' ? 'Elige un nombre, su nivel y las acciones que podrá hacer.' : actual?.descripcion
          }
          module="admin"
        />
        {!editable ? (
          <Alert tone="warning">
            Este rol es de tu nivel o de uno más alto: puedes consultarlo, pero no cambiarlo.
          </Alert>
        ) : null}
        {error ? <Alert tone="destructive">{error.message}</Alert> : null}

        <Card className="grid max-w-3xl grid-cols-1 gap-4 md:grid-cols-2">
          <Field
            label="Nombre"
            value={borrador.nombre}
            disabled={!editable}
            onChange={(e) => setBorrador({ ...borrador, nombre: e.target.value })}
          />
          <Field
            label="Nivel en la jerarquía"
            type="number"
            min={miNivel + 1}
            max={98}
            disabled={!editable}
            hint={`Un número mayor es un rol más bajo. Debe ser ${miNivel + 1} o más.`}
            value={String(borrador.nivel)}
            onChange={(e) => setBorrador({ ...borrador, nivel: Number(e.target.value) })}
          />
          <div className="md:col-span-2">
            <Field
              label="Descripción"
              value={borrador.descripcion}
              disabled={!editable}
              onChange={(e) => setBorrador({ ...borrador, descripcion: e.target.value })}
            />
          </div>
          <div className="md:col-span-2">
            <CheckboxField
              label="Exigir contraseña fuerte (en lugar de PIN)"
              checked={borrador.exige_credencial_fuerte}
              disabled={!editable}
              onChange={(e) => setBorrador({ ...borrador, exige_credencial_fuerte: e.target.checked })}
            />
          </div>
        </Card>

        {catalogo.data?.map((m) => (
          <Card key={m.modulo} className="flex flex-col gap-4">
            <CardTitle>{m.modulo}</CardTitle>
            {m.pantallas.map((p) => (
              <fieldset key={p.pantalla} className="flex flex-col gap-1">
                <legend className="font-bold">{p.pantalla}</legend>
                {p.acciones.map((a) => {
                  const tiene = marcados.has(a.codigo)
                  // Solo se concede lo que uno mismo tiene; lo que el rol ya tenía se puede quitar
                  const ajeno = !mios.has(a.codigo) && !tiene
                  return (
                    <div key={a.codigo} className="flex flex-wrap items-center gap-x-3">
                      <CheckboxField
                        label={a.accion}
                        checked={tiene}
                        disabled={!editable || ajeno}
                        onChange={(e) => alternar(a.codigo, e.target.checked)}
                      />
                      {a.sensible ? <Badge tone="warning">Sensible</Badge> : null}
                      {ajeno && editable ? (
                        <span className="text-sm text-muted-foreground">No lo tienes, no puedes concederlo</span>
                      ) : null}
                    </div>
                  )
                })}
              </fieldset>
            ))}
          </Card>
        ))}

        <div className="flex flex-wrap items-center gap-3">
          {editable ? (
            <Button onClick={() => guardar.mutate()} disabled={guardar.isPending || !borrador.nombre.trim()}>
              Guardar rol
            </Button>
          ) : null}
          {clave !== 'nuevo' ? (
            <Button variant="outline" onClick={() => duplicar.mutate(clave)} disabled={duplicar.isPending}>
              Duplicar
            </Button>
          ) : null}
          {actual && editable && !actual.es_base && actual.activo ? (
            <ConfirmButton
              variant="outline"
              pregunta="¿Desactivar este rol?"
              etiquetaConfirmar="Sí, desactivar"
              onConfirm={() => cambiarEstado.mutate({ rolClave: actual.clave, activar: false })}
            >
              Desactivar
            </ConfirmButton>
          ) : null}
          {actual && editable && !actual.activo ? (
            <Button
              variant="success"
              onClick={() => cambiarEstado.mutate({ rolClave: actual.clave, activar: true })}
            >
              Activar
            </Button>
          ) : null}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Roles y permisos"
        description="Crea roles y elige, por módulo y pantalla, lo que puede hacer cada uno."
        module="admin"
        actions={
          <Button
            onClick={() => {
              setClave('nuevo')
              setBorrador(vacio(Math.min(98, miNivel + 1)))
            }}
          >
            <Plus aria-hidden className="size-5" />
            Nuevo rol
          </Button>
        }
      />
      <CardDescription>
        Nadie está por encima del Super Usuario. Solo puedes crear o cambiar roles de un nivel más bajo
        que el tuyo y conceder lo que tú mismo puedes hacer.
      </CardDescription>
      <Card className="flex flex-col gap-2">
        <CardTitle>Roles de grupos y ministerios</CardTitle>
        <CardDescription>
          Encargado, respaldo, servidor y los demás roles que se tienen dentro de un grupo de conexión
          o de un ministerio se configuran aparte.
        </CardDescription>
        <Link to="/permisos/equipos" className="presionable w-fit font-semibold text-primary">
          Configurar roles de grupos y ministerios
        </Link>
      </Card>
      {error ? <Alert tone="destructive">{error.message}</Alert> : null}
      <Table aria-label="Roles del sistema">
        <TableHead>
          <TableRow className="hover:bg-muted">
            <TableHeaderCell>Rol</TableHeaderCell>
            <TableHeaderCell>Nivel</TableHeaderCell>
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
              <TableCell>{r.nivel}</TableCell>
              <TableCell>{r.usuarios}</TableCell>
              <TableCell>{r.permisos.length}</TableCell>
              <TableCell>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setClave(r.clave)
                    setBorrador({
                      nombre: r.nombre,
                      descripcion: r.descripcion,
                      nivel: r.nivel,
                      exige_credencial_fuerte: r.exige_credencial_fuerte,
                      permisos: r.permisos,
                    })
                  }}
                >
                  {r.editable ? 'Editar' : 'Ver'}
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

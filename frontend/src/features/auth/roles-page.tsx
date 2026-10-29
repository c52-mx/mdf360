import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  CheckboxField,
  Field,
  PageHeader,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '@/design-system'
import { api } from '@/lib/api'
import { useCan, type User } from './use-auth'

interface PermisosPersona {
  modulo: string
  pantalla: string
  acciones: { codigo: string; accion: string; sensible: boolean; roles: string[] }[]
}

interface Rol {
  clave: string
  nombre: string
  nivel: number
}

export function RolesPage() {
  const puede = useCan('roles.gestionar')
  const queryClient = useQueryClient()
  const [editando, setEditando] = useState<number | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const roles = useQuery({ queryKey: ['roles'], queryFn: () => api<Rol[]>('/api/auth/roles/'), enabled: puede })
  const usuarios = useQuery({ queryKey: ['usuarios'], queryFn: () => api<User[]>('/api/auth/users/'), enabled: puede })

  const permisosDe = useQuery({
    queryKey: ['permisos-de', editando, usuarios.dataUpdatedAt],
    enabled: puede && editando !== null,
    queryFn: () => api<PermisosPersona[]>(`/api/auth/users/${editando}/permisos/`),
  })

  const guardar = useMutation({
    mutationFn: ({ id, claves }: { id: number; claves: string[] }) =>
      api<User>(`/api/auth/users/${id}/roles/`, { method: 'POST', body: { roles: claves } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['usuarios'] }),
  })

  if (!puede) return <Alert tone="warning">No tienes permiso para asignar roles.</Alert>

  const nombreDe = (clave: string) => roles.data?.find((r) => r.clave === clave)?.nombre ?? clave
  const alternar = (u: User, clave: string, activo: boolean) =>
    guardar.mutate({
      id: u.id,
      claves: activo ? [...u.roles, clave] : u.roles.filter((r) => r !== clave),
    })

  const elegido = usuarios.data?.find((u) => u.id === editando)
  if (elegido) {
    return (
      <div className="flex flex-col gap-6">
        <button
          type="button"
          onClick={() => {
            guardar.reset()
            setEditando(null)
          }}
          className="presionable flex w-fit items-center gap-2 font-semibold text-primary"
        >
          <ArrowLeft aria-hidden className="size-5" />
          Volver al listado
        </button>
        <PageHeader title={elegido.nombre} description={elegido.whatsapp} module="admin" />
        {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
        <Card className="flex flex-col gap-2">
          <CardTitle>Roles de {elegido.nombre}</CardTitle>
          <CardDescription>Los cambios se guardan al marcar o desmarcar.</CardDescription>
          <div className="grid grid-cols-1 gap-x-4 md:grid-cols-3">
            {roles.data?.map((r) => (
              <CheckboxField
                key={r.clave}
                label={r.nombre}
                checked={elegido.roles.includes(r.clave)}
                disabled={guardar.isPending}
                onChange={(e) => alternar(elegido, r.clave, e.target.checked)}
              />
            ))}
          </div>
        </Card>
        <Card className="flex flex-col gap-3">
          <CardTitle>Lo que puede hacer</CardTitle>
          {permisosDe.data?.length === 0 ? (
            <CardDescription>Sus roles no le dan acciones administrativas.</CardDescription>
          ) : null}
          {permisosDe.data?.map((f) => (
            <div key={`${f.modulo}-${f.pantalla}`} className="flex flex-col gap-1">
              <p className="font-bold">
                {f.modulo} › {f.pantalla}
              </p>
              <ul className="flex flex-col gap-1">
                {f.acciones.map((a) => (
                  <li key={a.codigo} className="flex flex-wrap items-center gap-2">
                    <span>{a.accion}</span>
                    {a.sensible ? <Badge tone="warning">Sensible</Badge> : null}
                    <span className="text-sm text-muted-foreground">por {a.roles.join(', ')}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </Card>
      </div>
    )
  }

  const texto = busqueda.trim().toLowerCase()
  const filas = (usuarios.data ?? []).filter(
    (u) => !texto || u.nombre.toLowerCase().includes(texto) || u.whatsapp.includes(texto),
  )

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Roles" description="Asigna a cada persona los roles que le corresponden." module="admin" />
      <Card>
        <Field
          label="Buscar por nombre o WhatsApp"
          type="search"
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
        />
      </Card>
      {usuarios.isError ? <Alert tone="destructive">{usuarios.error.message}</Alert> : null}
      {usuarios.data && filas.length === 0 ? <Alert>No hay personas con ese dato.</Alert> : null}
      {filas.length > 0 ? (
        <Table aria-label="Personas con acceso y sus roles">
          <TableHead>
            <TableRow className="hover:bg-muted">
              <TableHeaderCell>Persona</TableHeaderCell>
              <TableHeaderCell>WhatsApp</TableHeaderCell>
              <TableHeaderCell>Roles</TableHeaderCell>
              <TableHeaderCell>
                <span className="sr-only">Acciones</span>
              </TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filas.map((u) => (
              <TableRow key={u.id}>
                <TableCell className="font-bold">{u.nombre}</TableCell>
                <TableCell>{u.whatsapp}</TableCell>
                <TableCell>
                  {u.roles.length > 0 ? (
                    <span className="flex flex-wrap gap-1">
                      {u.roles.map((r) => (
                        <Badge key={r} tone="primary">
                          {nombreDe(r)}
                        </Badge>
                      ))}
                    </span>
                  ) : (
                    <Badge tone="warning">Sin rol</Badge>
                  )}
                </TableCell>
                <TableCell>
                  <Button size="sm" variant="outline" onClick={() => setEditando(u.id)}>
                    Asignar roles
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : null}
    </div>
  )
}

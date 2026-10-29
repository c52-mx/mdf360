import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
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
  SelectField,
  useToast,
} from '@/design-system'
import { opcionesDeRol, useRolesEquipo } from '@/features/equipos/use-roles-equipo'
import { TableroPanel } from '@/features/tablero/tablero-panel'
import { api } from '@/lib/api'
import type { UnidadDetalle } from './types'

export function UnidadPage() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [whatsapp, setWhatsapp] = useState('')
  const [nombre, setNombre] = useState('')
  const [rol, setRol] = useState('servidor')
  const [acepta, setAcepta] = useState(false)
  const [editando, setEditando] = useState(false)
  const [form, setForm] = useState({ nombre: '', descripcion: '' })

  const roles = useRolesEquipo('ministerio')
  const unidad = useQuery({
    queryKey: ['unidad', id],
    queryFn: () => api<UnidadDetalle>(`/api/unidades/${id}/`),
  })
  const refrescar = () => {
    void queryClient.invalidateQueries({ queryKey: ['unidad', id] })
    void queryClient.invalidateQueries({ queryKey: ['unidades'] })
  }

  const agregar = useMutation({
    mutationFn: () =>
      api(`/api/unidades/${id}/integrantes/`, {
        method: 'POST',
        body: { whatsapp, nombre, rol, acepta_datos: acepta },
      }),
    onSuccess: () => {
      setWhatsapp('')
      setNombre('')
      setAcepta(false)
      refrescar()
    },
  })
  const restaurar = useMutation({
    mutationFn: (miembroId: number) =>
      api(`/api/unidades/${id}/integrantes/${miembroId}/restaurar/`, { method: 'POST', body: {} }),
    onSuccess: refrescar,
  })
  const restaurarIntegrante = restaurar.mutate
  const quitar = useMutation({
    mutationFn: ({ miembroId }: { miembroId: number; nombre: string }) =>
      api(`/api/unidades/${id}/integrantes/${miembroId}/`, { method: 'DELETE' }),
    onSuccess: (_, { miembroId, nombre: quien }) => {
      refrescar()
      toast.mostrar(`${quien} salió del ministerio.`, {
        etiqueta: 'Deshacer',
        onClick: () => restaurarIntegrante(miembroId),
      })
    },
  })
  const cambiarRol = useMutation({
    mutationFn: ({ miembroId, nuevo }: { miembroId: number; nuevo: string }) =>
      api(`/api/unidades/${id}/integrantes/${miembroId}/`, { method: 'PATCH', body: { rol: nuevo } }),
    onSuccess: refrescar,
  })
  const guardar = useMutation({
    mutationFn: () => api(`/api/unidades/${id}/`, { method: 'PATCH', body: form }),
    onSuccess: () => {
      setEditando(false)
      toast.mostrar('Los datos del ministerio se guardaron.')
      refrescar()
    },
  })

  if (unidad.isPending) return <p className="text-muted-foreground">Cargando…</p>
  if (unidad.isError) return <Alert tone="destructive">{unidad.error.message}</Alert>
  const u = unidad.data
  const opciones = opcionesDeRol(roles.data, u.puede_administrar)
  const deGestion = (clave: string) => roles.data?.find((r) => r.clave === clave)?.de_gestion ?? false

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    agregar.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <Link to="/ministerios" className="presionable flex w-fit items-center gap-2 font-semibold text-primary">
        <ArrowLeft aria-hidden className="size-5" />
        Volver a ministerios
      </Link>
      <PageHeader title={u.nombre} description={u.descripcion || undefined} module="grupos" />

      <Card className="flex flex-col gap-3">
        <CardTitle>Integrantes</CardTitle>
        <ul className="flex flex-col gap-2">
          {u.miembros.map((m) => (
            <li key={m.id} className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <span className="font-bold">{m.nombre}</span>{' '}
                <Badge tone={m.rol === 'servidor' ? 'neutral' : 'primary'}>{m.rol_display}</Badge>
              </span>
              {u.puede_gestionar && (u.puede_administrar || !deGestion(m.rol)) ? (
                <span className="flex flex-wrap items-center gap-2">
                  <select
                    aria-label={`Rol de ${m.nombre}`}
                    value={m.rol}
                    disabled={cambiarRol.isPending}
                    onChange={(e) => cambiarRol.mutate({ miembroId: m.id, nuevo: e.target.value })}
                    className="h-10 rounded-control border-2 border-border bg-card px-2"
                  >
                    {opciones.map((r) => (
                      <option key={r.value} value={r.value}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => quitar.mutate({ miembroId: m.id, nombre: m.nombre })}
                  >
                    Quitar
                  </Button>
                </span>
              ) : null}
            </li>
          ))}
        </ul>
        {quitar.error ? <Alert tone="destructive">{quitar.error.message}</Alert> : null}
        {cambiarRol.error ? <Alert tone="destructive">{cambiarRol.error.message}</Alert> : null}
      </Card>

      {u.puede_gestionar ? (
        <Card>
          <form onSubmit={onSubmit} className="grid max-w-xl grid-cols-1 gap-4">
            <CardTitle>Agregar una persona</CardTitle>
            <CardDescription>
              Si el número ya está registrado, se vincula a la misma persona sin duplicarla.
            </CardDescription>
            <Field
              label="WhatsApp"
              inputMode="tel"
              value={whatsapp}
              onChange={(e) => setWhatsapp(e.target.value)}
              required
            />
            <Field label="Nombre (si es nueva)" value={nombre} onChange={(e) => setNombre(e.target.value)} />
            <SelectField label="Rol en el ministerio" value={rol} onChange={(e) => setRol(e.target.value)} options={opciones} />
            <CheckboxField
              checked={acepta}
              onChange={(e) => setAcepta(e.target.checked)}
              label="La persona nueva acepta el aviso de privacidad"
            />
            {agregar.error ? <Alert tone="destructive">{agregar.error.message}</Alert> : null}
            <Button type="submit" disabled={agregar.isPending}>
              Agregar
            </Button>
          </form>
        </Card>
      ) : null}

      {u.puede_administrar ? (
        <Card className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>Datos del ministerio</CardTitle>
            {!editando ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setForm({ nombre: u.nombre, descripcion: u.descripcion })
                  setEditando(true)
                }}
              >
                Editar datos
              </Button>
            ) : null}
          </div>
          {editando ? (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                guardar.mutate()
              }}
              className="grid max-w-xl grid-cols-1 gap-4"
            >
              <Field label="Nombre" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
              <Field
                label="Descripción"
                value={form.descripcion}
                onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
              />
              {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={guardar.isPending}>
                  Guardar
                </Button>
                <Button type="button" variant="outline" onClick={() => setEditando(false)}>
                  Cancelar
                </Button>
              </div>
            </form>
          ) : (
            <CardDescription>{u.descripcion || 'Sin descripción.'}</CardDescription>
          )}
        </Card>
      ) : null}

      <TableroPanel origenTipo="unidad" origenId={u.id} puedePublicar={u.puede_gestionar} />
    </div>
  )
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
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
  SelectField,
  TextareaField,
  useToast,
} from '@/design-system'
import { opcionesDeRol, useRolesEquipo } from '@/features/equipos/use-roles-equipo'
import { PeticionesPanel } from '@/features/peticiones/peticiones-panel'
import { TableroPanel } from '@/features/tablero/tablero-panel'
import { api } from '@/lib/api'
import { esErrorDeRed } from '@/lib/outbox'
import { IngresoCard } from './ingreso-card'
import { dinero } from './ofrendas'
import { dias, fechaLarga, SECTORES, type GrupoDetalle } from './types'

export function GrupoPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const [whatsapp, setWhatsapp] = useState('')
  const [nombre, setNombre] = useState('')
  const [rol, setRol] = useState('asistente')
  const [acepta, setAcepta] = useState(false)
  const [editando, setEditando] = useState(false)
  const [form, setForm] = useState({ nombre: '', sector: '', casa: '', dia: '', hora: '', colonia: '' })
  const [motivo, setMotivo] = useState('')

  const roles = useRolesEquipo('grupo')
  const grupo = useQuery({
    queryKey: ['grupo', id],
    queryFn: () => api<GrupoDetalle>(`/api/grupos/${id}/`),
  })
  const refrescar = () => queryClient.invalidateQueries({ queryKey: ['grupo', id] })

  const agregar = useMutation({
    mutationFn: () =>
      api(`/api/grupos/${id}/integrantes/`, {
        method: 'POST',
        body: { whatsapp, nombre, rol, acepta_datos: acepta },
      }),
    onSuccess: () => {
      setWhatsapp('')
      setNombre('')
      setAcepta(false)
      void refrescar()
    },
  })
  const restaurar = useMutation({
    mutationFn: (miembroId: number) =>
      api(`/api/grupos/${id}/integrantes/${miembroId}/restaurar/`, { method: 'POST', body: {} }),
    onSuccess: () => void refrescar(),
  })
  const restaurarIntegrante = restaurar.mutate
  const quitar = useMutation({
    mutationFn: ({ miembroId }: { miembroId: number; nombre: string }) =>
      api(`/api/grupos/${id}/integrantes/${miembroId}/`, { method: 'DELETE' }),
    onSuccess: (_, { miembroId, nombre: quien }) => {
      void refrescar()
      // Se quita al instante, pero se puede deshacer unos segundos
      toast.mostrar(`${quien} salió del grupo.`, {
        etiqueta: 'Deshacer',
        onClick: () => restaurarIntegrante(miembroId),
      })
    },
  })
  const guardarGrupo = useMutation({
    mutationFn: () =>
      api(`/api/grupos/${id}/`, {
        method: 'PATCH',
        body: {
          nombre: form.nombre,
          sector: form.sector,
          casa: form.casa === '' ? null : Number(form.casa),
          dia_semana: form.dia === '' ? null : Number(form.dia),
          hora: form.hora || null,
          colonia: form.colonia,
        },
      }),
    onSuccess: () => {
      setEditando(false)
      toast.mostrar('Los datos del grupo se guardaron.')
      void refrescar()
      void queryClient.invalidateQueries({ queryKey: ['grupos'] })
    },
  })
  const suspender = useMutation({
    mutationFn: () => api(`/api/grupos/${id}/suspender/`, { method: 'POST', body: { motivo } }),
    onSuccess: () => {
      setMotivo('')
      toast.mostrar('El grupo quedó suspendido.')
      void refrescar()
      void queryClient.invalidateQueries({ queryKey: ['grupos'] })
      void queryClient.invalidateQueries({ queryKey: ['grupos-dashboard'] })
    },
  })
  const reactivar = useMutation({
    mutationFn: () => api(`/api/grupos/${id}/reactivar/`, { method: 'POST', body: {} }),
    onSuccess: () => {
      toast.mostrar('El grupo volvió a estar activo.')
      void refrescar()
      void queryClient.invalidateQueries({ queryKey: ['grupos'] })
      void queryClient.invalidateQueries({ queryKey: ['grupos-dashboard'] })
    },
  })
  const cambiarRol = useMutation({
    mutationFn: ({ miembroId, nuevo }: { miembroId: number; nuevo: string }) =>
      api(`/api/grupos/${id}/integrantes/${miembroId}/`, { method: 'PATCH', body: { rol: nuevo } }),
    onSuccess: () => void refrescar(),
  })
  const abrir = useMutation({
    mutationFn: () =>
      api<{ id: number }>(`/api/grupos/${id}/reuniones/`, { method: 'POST', body: {} }),
    onSuccess: (r) => navigate(`/grupos/reuniones/${r.id}`),
    // Sin señal no se puede abrir la reunión en el servidor: se pasa lista en el teléfono
    onError: (error) => {
      if (esErrorDeRed(error)) navigate(`/grupos/${id}/hoy`)
    },
  })

  if (grupo.isPending) return <p className="text-muted-foreground">Cargando…</p>
  if (grupo.isError) return <Alert tone="destructive">{grupo.error.message}</Alert>
  const g = grupo.data
  const deGestion = (clave: string) => roles.data?.find((r) => r.clave === clave)?.de_gestion ?? false

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    agregar.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={g.nombre}
        description={[g.ubicacion, g.dia && `${g.dia} ${g.hora}`.trim(), g.colonia]
          .filter(Boolean)
          .join(' · ')}
        module="grupos"
        actions={
          g.puede_capturar && !g.suspendido ? (
            <Button onClick={() => abrir.mutate()} disabled={abrir.isPending}>
              Pasar lista de hoy
            </Button>
          ) : null
        }
      />
      {abrir.error ? <Alert tone="destructive">{abrir.error.message}</Alert> : null}
      {g.suspendido ? (
        <Alert tone="warning">
          Grupo suspendido
          {g.suspendido_en ? ` desde el ${fechaLarga(g.suspendido_en)}` : ''}. Motivo: {g.suspension_motivo}
        </Alert>
      ) : null}
      {g.ofrendas_con_diferencia ? (
        <Alert tone="destructive">
          Hay {g.ofrendas_con_diferencia === 1 ? '1 ofrenda' : `${g.ofrendas_con_diferencia} ofrendas`} con
          diferencia entre lo capturado y lo contado. Revísalas en la reunión correspondiente.
        </Alert>
      ) : null}

      <Card className="flex flex-col gap-3">
        <CardTitle>Integrantes</CardTitle>
        <ul className="flex flex-col gap-2">
          {g.miembros.map((m) => (
            <li key={m.id} className="flex flex-wrap items-center justify-between gap-2">
              <span>
                <span className="font-bold">{m.nombre}</span>{' '}
                <Badge tone={m.rol === 'asistente' ? 'neutral' : 'primary'}>{m.rol_display}</Badge>{' '}
                {m.invitado ? <Badge tone="warning">Invitado</Badge> : null}
              </span>
              {g.puede_gestionar && (g.puede_administrar || !deGestion(m.rol)) ? (
                <span className="flex flex-wrap items-center gap-2">
                  <select
                    aria-label={`Rol de ${m.nombre}`}
                    value={m.rol}
                    disabled={cambiarRol.isPending}
                    onChange={(e) => cambiarRol.mutate({ miembroId: m.id, nuevo: e.target.value })}
                    className="h-10 rounded-control border-2 border-border bg-card px-2"
                  >
                    {opcionesDeRol(roles.data, g.puede_administrar)
                      .map((r) => (
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

      {g.puede_administrar ? (
        <Card className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>Datos del grupo</CardTitle>
            {!editando ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setForm({
                    nombre: g.nombre,
                    sector: g.sector,
                    casa: g.casa === null ? '' : String(g.casa),
                    dia: g.dia_semana === null ? '' : String(g.dia_semana),
                    hora: g.hora,
                    colonia: g.colonia,
                  })
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
                guardarGrupo.mutate()
              }}
              className="grid max-w-xl grid-cols-1 gap-4"
            >
              <Field
                label="Nombre"
                value={form.nombre}
                onChange={(e) => setForm({ ...form, nombre: e.target.value })}
                required
              />
              <div className="grid grid-cols-2 gap-4">
                <SelectField
                  label="Sector"
                  value={form.sector}
                  onChange={(e) => setForm({ ...form, sector: e.target.value })}
                  options={[
                    { value: '', label: 'Sin definir' },
                    ...SECTORES.map((s) => ({ value: s, label: s })),
                  ]}
                />
                <Field
                  label="Casa"
                  type="number"
                  min={1}
                  inputMode="numeric"
                  value={form.casa}
                  onChange={(e) => setForm({ ...form, casa: e.target.value })}
                />
              </div>
              <SelectField
                label="Día de reunión"
                value={form.dia}
                onChange={(e) => setForm({ ...form, dia: e.target.value })}
                options={[
                  { value: '', label: 'Sin definir' },
                  ...dias.map((d, i) => ({ value: String(i), label: d })),
                ]}
              />
              <Field
                label="Hora"
                type="time"
                value={form.hora}
                onChange={(e) => setForm({ ...form, hora: e.target.value })}
              />
              <Field
                label="Zona o colonia"
                value={form.colonia}
                onChange={(e) => setForm({ ...form, colonia: e.target.value })}
              />
              {guardarGrupo.error ? <Alert tone="destructive">{guardarGrupo.error.message}</Alert> : null}
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={guardarGrupo.isPending}>
                  Guardar
                </Button>
                <Button type="button" variant="outline" onClick={() => setEditando(false)}>
                  Cancelar
                </Button>
              </div>
            </form>
          ) : (
            <CardDescription>
              {[g.ubicacion, g.dia && `${g.dia} ${g.hora}`.trim(), g.colonia].filter(Boolean).join(' · ') ||
                'Aún sin sector, día ni colonia.'}
            </CardDescription>
          )}

          {g.suspendido ? (
            <div className="flex flex-wrap items-center gap-3">
              <Button variant="success" onClick={() => reactivar.mutate()} disabled={reactivar.isPending}>
                Reactivar grupo
              </Button>
              {reactivar.error ? <Alert tone="destructive">{reactivar.error.message}</Alert> : null}
            </div>
          ) : (
            <div className="flex max-w-xl flex-col gap-3">
              <TextareaField
                label="Suspender el grupo"
                hint="Un grupo suspendido no abre reuniones ni cuenta en el resumen. Escribe el motivo."
                value={motivo}
                onChange={(e) => setMotivo(e.target.value)}
              />
              {suspender.error ? <Alert tone="destructive">{suspender.error.message}</Alert> : null}
              {motivo.trim() ? (
                <ConfirmButton
                  variant="outline"
                  pregunta="¿Suspender este grupo?"
                  etiquetaConfirmar="Sí, suspender"
                  onConfirm={() => suspender.mutate()}
                >
                  Suspender grupo
                </ConfirmButton>
              ) : null}
            </div>
          )}
        </Card>
      ) : null}

      {g.puede_gestionar ? (
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
            <Field
              label="Nombre (si es nueva)"
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
            />
            <SelectField
              label="Rol en el grupo"
              value={rol}
              onChange={(e) => setRol(e.target.value)}
              options={opcionesDeRol(roles.data, g.puede_administrar)}
            />
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

      {g.puede_gestionar ? (
        <IngresoCard grupoId={g.id} enlace={g.enlace} suspendido={g.suspendido} />
      ) : null}

      <TableroPanel
        origenTipo="grupo"
        origenId={g.id}
        puedePublicar={g.mis_roles.some((r) => ['lider', 'supervisor', 'secretario'].includes(r)) || g.puede_administrar}
      />

      <PeticionesPanel origenTipo="grupo" origenId={g.id} puedeRegistrar={g.puede_capturar} />

      <Card className="flex flex-col gap-3">
        <CardTitle>Reuniones</CardTitle>
        {g.reuniones.length === 0 ? (
          <CardDescription>Aún no hay reuniones registradas.</CardDescription>
        ) : (
          <ul className="flex flex-col gap-2">
            {g.reuniones.map((r) => (
              <li key={r.id} className="flex flex-col gap-1 border-b border-border pb-2 last:border-b-0">
                <Link
                  className="flex flex-wrap justify-between gap-2 font-bold underline"
                  to={`/grupos/reuniones/${r.id}`}
                >
                  <span className="capitalize">{fechaLarga(r.fecha)}</span>
                  {r.registrados !== undefined ? (
                    <span className="font-normal text-muted-foreground">
                      {r.presentes} de {r.registrados} presentes
                    </span>
                  ) : null}
                </Link>
                {r.peticiones || r.ofrendas ? (
                  <span className="flex flex-wrap gap-2">
                    {r.peticiones ? (
                      <Badge tone="primary">
                        {r.peticiones === 1 ? '1 petición' : `${r.peticiones} peticiones`}
                      </Badge>
                    ) : null}
                    {r.ofrendas && r.ofrendas.cantidad > 0 ? (
                      <Badge tone="neutral">Ofrendas: {dinero(r.ofrendas.total)}</Badge>
                    ) : null}
                  </span>
                ) : null}
                {r.notas ? <CardDescription>Observaciones: {r.notas}</CardDescription> : null}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

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
  Field,
  PageHeader,
  SelectField,
} from '@/design-system'
import { api } from '@/lib/api'
import { fechaLarga, rolesGrupo, type GrupoDetalle } from './types'

const RESERVADOS = ['lider', 'supervisor']

export function GrupoPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [whatsapp, setWhatsapp] = useState('')
  const [nombre, setNombre] = useState('')
  const [rol, setRol] = useState('asistente')
  const [acepta, setAcepta] = useState(false)

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
  const quitar = useMutation({
    mutationFn: (miembroId: number) =>
      api(`/api/grupos/${id}/integrantes/${miembroId}/`, { method: 'DELETE' }),
    onSuccess: () => void refrescar(),
  })
  const abrir = useMutation({
    mutationFn: () =>
      api<{ id: number }>(`/api/grupos/${id}/reuniones/`, { method: 'POST', body: {} }),
    onSuccess: (r) => navigate(`/grupos/reuniones/${r.id}`),
  })

  if (grupo.isPending) return <p className="text-muted-foreground">Cargando…</p>
  if (grupo.isError) return <Alert tone="destructive">{grupo.error.message}</Alert>
  const g = grupo.data

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    agregar.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={g.nombre}
        description={[g.dia && `${g.dia} ${g.hora}`.trim(), g.colonia].filter(Boolean).join(' · ')}
        module="grupos"
        actions={
          g.puede_capturar ? (
            <Button onClick={() => abrir.mutate()} disabled={abrir.isPending}>
              Pasar lista de hoy
            </Button>
          ) : null
        }
      />
      {abrir.error ? <Alert tone="destructive">{abrir.error.message}</Alert> : null}
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
              {g.puede_gestionar && (g.puede_administrar || !RESERVADOS.includes(m.rol)) ? (
                <Button size="sm" variant="ghost" onClick={() => quitar.mutate(m.id)}>
                  Quitar
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
        {quitar.error ? <Alert tone="destructive">{quitar.error.message}</Alert> : null}
      </Card>

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
              options={rolesGrupo.filter((r) => g.puede_administrar || !RESERVADOS.includes(r.value))}
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

      <Card className="flex flex-col gap-3">
        <CardTitle>Reuniones</CardTitle>
        {g.reuniones.length === 0 ? (
          <CardDescription>Aún no hay reuniones registradas.</CardDescription>
        ) : (
          <ul className="flex flex-col gap-2">
            {g.reuniones.map((r) => (
              <li key={r.id}>
                <Link
                  className="flex flex-wrap justify-between gap-2 underline"
                  to={`/grupos/reuniones/${r.id}`}
                >
                  <span className="capitalize">{fechaLarga(r.fecha)}</span>
                  {r.registrados !== undefined ? (
                    <span className="text-muted-foreground">
                      {r.presentes} de {r.registrados} presentes
                    </span>
                  ) : null}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardLink,
  CardDescription,
  CardTitle,
  Field,
  PageHeader,
  SelectField,
} from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'
import { dias, SECTORES, type GrupoResumen } from './types'

export function GruposPage() {
  const queryClient = useQueryClient()
  const puedeCrear = useCan('grupos.gestionar')
  const [creando, setCreando] = useState(false)
  const [nombre, setNombre] = useState('')
  const [tipo, setTipo] = useState('conexion')
  const [dia, setDia] = useState('')
  const [hora, setHora] = useState('')
  const [colonia, setColonia] = useState('')
  const [sector, setSector] = useState('')
  const [casa, setCasa] = useState('')
  const [q, setQ] = useState('')
  const [filtroDia, setFiltroDia] = useState('')
  const [filtroSector, setFiltroSector] = useState('')
  const [filtroLider, setFiltroLider] = useState('')
  const [estado, setEstado] = useState('')

  const grupos = useQuery({
    queryKey: ['grupos', { q, filtroDia, filtroSector, filtroLider, estado }],
    placeholderData: (previo) => previo,
    queryFn: () => {
      const params = new URLSearchParams()
      if (q.trim()) params.set('q', q.trim())
      if (filtroDia) params.set('dia', filtroDia)
      if (filtroSector) params.set('sector', filtroSector)
      if (filtroLider.trim()) params.set('lider', filtroLider.trim())
      if (estado) params.set('estado', estado)
      return api<GrupoResumen[]>(`/api/grupos/?${params.toString()}`)
    },
  })
  const crear = useMutation({
    mutationFn: () =>
      api<GrupoResumen>('/api/grupos/', {
        method: 'POST',
        body: {
          nombre,
          tipo,
          colonia,
          sector,
          casa: casa === '' ? null : Number(casa),
          dia_semana: dia === '' ? null : Number(dia),
          hora: hora || null,
        },
      }),
    onSuccess: () => {
      setCreando(false)
      setNombre('')
      setSector('')
      setCasa('')
      void queryClient.invalidateQueries({ queryKey: ['grupos'] })
    },
  })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    crear.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Grupos de Conexión"
        description="Tus grupos y reuniones."
        module="grupos"
        actions={
          <>
            <Button asChild variant="outline">
              <Link to="/estudios">
                <BookOpen aria-hidden className="size-5" />
                Estudio de la semana
              </Link>
            </Button>
            {puedeCrear ? (
              <Button onClick={() => setCreando((v) => !v)}>
                <Plus aria-hidden className="size-5" />
                Nuevo grupo
              </Button>
            ) : null}
          </>
        }
      />

      {creando ? (
        <Card>
          <form onSubmit={onSubmit} className="grid max-w-xl grid-cols-1 gap-4">
            <CardTitle>Nuevo grupo</CardTitle>
            <Field label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
            <SelectField
              label="Tipo"
              value={tipo}
              onChange={(e) => setTipo(e.target.value)}
              options={[
                { value: 'conexion', label: 'Grupo de Conexión' },
                { value: 'lideres', label: 'Reunión general de líderes' },
              ]}
            />
            <SelectField
              label="Día de reunión"
              value={dia}
              onChange={(e) => setDia(e.target.value)}
              options={[
                { value: '', label: 'Sin definir' },
                ...dias.map((d, i) => ({ value: String(i), label: d })),
              ]}
            />
            <Field label="Hora" type="time" value={hora} onChange={(e) => setHora(e.target.value)} />
            <div className="grid grid-cols-2 gap-4">
              <SelectField
                label="Sector"
                value={sector}
                onChange={(e) => setSector(e.target.value)}
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
                value={casa}
                onChange={(e) => setCasa(e.target.value)}
              />
            </div>
            <Field
              label="Zona o colonia"
              hint="No escribas el domicilio exacto del anfitrión."
              value={colonia}
              onChange={(e) => setColonia(e.target.value)}
            />
            {crear.error ? <Alert tone="destructive">{crear.error.message}</Alert> : null}
            <Button type="submit" disabled={crear.isPending}>
              Guardar grupo
            </Button>
          </form>
        </Card>
      ) : null}

      <Card className="grid grid-cols-1 gap-4 md:grid-cols-5">
        <Field
          label="Buscar"
          type="search"
          placeholder="Nombre o colonia"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <Field
          label="Líder"
          type="search"
          placeholder="Nombre del líder"
          value={filtroLider}
          onChange={(e) => setFiltroLider(e.target.value)}
        />
        <SelectField
          label="Día"
          value={filtroDia}
          onChange={(e) => setFiltroDia(e.target.value)}
          options={[{ value: '', label: 'Todos' }, ...dias.map((d, i) => ({ value: String(i), label: d }))]}
        />
        <SelectField
          label="Sector"
          value={filtroSector}
          onChange={(e) => setFiltroSector(e.target.value)}
          options={[{ value: '', label: 'Todos' }, ...SECTORES.map((s) => ({ value: s, label: s }))]}
        />
        <SelectField
          label="Estado"
          value={estado}
          onChange={(e) => setEstado(e.target.value)}
          options={[
            { value: '', label: 'Todos' },
            { value: 'activos', label: 'Activos' },
            { value: 'suspendidos', label: 'Suspendidos' },
          ]}
        />
      </Card>

      {grupos.isError ? <Alert tone="destructive">{grupos.error.message}</Alert> : null}
      {grupos.data && grupos.data.length === 0 ? (
        <Alert>No hay grupos con esos filtros, o todavía no perteneces a ninguno.</Alert>
      ) : null}
      <ul className="flex flex-col gap-3">
        {grupos.data?.map((g) => (
          <li key={g.id}>
            <CardLink to={`/grupos/${g.id}`} className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle>{g.nombre}</CardTitle>
                  <CardDescription>
                    {[g.dia && `${g.dia} ${g.hora}`.trim(), g.ubicacion, g.colonia, `${g.integrantes} integrantes`]
                      .filter(Boolean)
                      .join(' · ')}
                  </CardDescription>
                  {g.lideres.length ? (
                    <CardDescription>Líder: {g.lideres.join(', ')}</CardDescription>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  {g.ofrendas_con_diferencia ? (
                    <Badge tone="destructive">
                      {g.ofrendas_con_diferencia === 1
                        ? '1 ofrenda con diferencia'
                        : `${g.ofrendas_con_diferencia} ofrendas con diferencia`}
                    </Badge>
                  ) : null}
                  {g.suspendido ? <Badge tone="warning">Suspendido</Badge> : null}
                  {g.tipo === 'lideres' ? <Badge tone="primary">Líderes</Badge> : null}
                  {g.mis_roles.map((r) => (
                    <Badge key={r} tone="success">
                      {r}
                    </Badge>
                  ))}
                </div>
            </CardLink>
          </li>
        ))}
      </ul>
    </div>
  )
}

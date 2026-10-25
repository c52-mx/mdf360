import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  Field,
  PageHeader,
  SelectField,
} from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'
import { dias, type GrupoResumen } from './types'

export function GruposPage() {
  const queryClient = useQueryClient()
  const puedeCrear = useCan('grupos.gestionar')
  const [creando, setCreando] = useState(false)
  const [nombre, setNombre] = useState('')
  const [tipo, setTipo] = useState('conexion')
  const [dia, setDia] = useState('')
  const [hora, setHora] = useState('')
  const [colonia, setColonia] = useState('')

  const grupos = useQuery({ queryKey: ['grupos'], queryFn: () => api<GrupoResumen[]>('/api/grupos/') })
  const crear = useMutation({
    mutationFn: () =>
      api<GrupoResumen>('/api/grupos/', {
        method: 'POST',
        body: {
          nombre,
          tipo,
          colonia,
          dia_semana: dia === '' ? null : Number(dia),
          hora: hora || null,
        },
      }),
    onSuccess: () => {
      setCreando(false)
      setNombre('')
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

      {grupos.isError ? <Alert tone="destructive">{grupos.error.message}</Alert> : null}
      {grupos.data && grupos.data.length === 0 ? (
        <Alert>Todavía no perteneces a ningún grupo.</Alert>
      ) : null}
      <ul className="flex flex-col gap-3">
        {grupos.data?.map((g) => (
          <li key={g.id}>
            <Link to={`/grupos/${g.id}`} className="block rounded-card">
              <Card className="flex flex-wrap items-center justify-between gap-3 hover:bg-primary-soft">
                <div>
                  <CardTitle>{g.nombre}</CardTitle>
                  <CardDescription>
                    {[g.dia && `${g.dia} ${g.hora}`.trim(), g.colonia, `${g.integrantes} integrantes`]
                      .filter(Boolean)
                      .join(' · ')}
                  </CardDescription>
                  {g.lideres.length ? (
                    <CardDescription>Líder: {g.lideres.join(', ')}</CardDescription>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  {g.tipo === 'lideres' ? <Badge tone="primary">Líderes</Badge> : null}
                  {g.mis_roles.map((r) => (
                    <Badge key={r} tone="success">
                      {r}
                    </Badge>
                  ))}
                </div>
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

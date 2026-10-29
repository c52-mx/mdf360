import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardLink,
  CardTitle,
  Field,
  PageHeader,
} from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'
import type { UnidadResumen } from './types'

/** Los ministerios (áreas de servicio) donde la persona participa o, si administra, todas. */
export function UnidadesPage() {
  const queryClient = useQueryClient()
  const puedeCrear = useCan('unidades.gestionar')
  const [creando, setCreando] = useState(false)
  const [nombre, setNombre] = useState('')
  const [descripcion, setDescripcion] = useState('')

  const unidades = useQuery({
    queryKey: ['unidades'],
    queryFn: () => api<UnidadResumen[]>('/api/unidades/'),
  })
  const crear = useMutation({
    mutationFn: () => api<UnidadResumen>('/api/unidades/', { method: 'POST', body: { nombre, descripcion } }),
    onSuccess: () => {
      setCreando(false)
      setNombre('')
      setDescripcion('')
      void queryClient.invalidateQueries({ queryKey: ['unidades'] })
    },
  })

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    crear.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Ministerios"
        description="Áreas de servicio de la iglesia: cafetería, librería, niños, danza y más."
        module="grupos"
        actions={
          puedeCrear ? (
            <Button onClick={() => setCreando((v) => !v)}>
              <Plus aria-hidden className="size-5" />
              Nuevo ministerio
            </Button>
          ) : null
        }
      />

      {creando ? (
        <Card>
          <form onSubmit={onSubmit} className="grid max-w-xl grid-cols-1 gap-4">
            <CardTitle>Nuevo ministerio</CardTitle>
            <Field label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
            <Field
              label="Descripción (opcional)"
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
            />
            {crear.error ? <Alert tone="destructive">{crear.error.message}</Alert> : null}
            <Button type="submit" disabled={crear.isPending || !nombre.trim()}>
              Guardar ministerio
            </Button>
          </form>
        </Card>
      ) : null}

      {unidades.isError ? <Alert tone="destructive">{unidades.error.message}</Alert> : null}
      {unidades.data && unidades.data.length === 0 ? (
        <Alert>Todavía no participas en ningún ministerio.</Alert>
      ) : null}
      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {unidades.data?.map((u) => (
          <li key={u.id}>
            <CardLink to={`/ministerios/${u.id}`} className="flex h-full flex-col gap-1">
              <CardTitle>{u.nombre}</CardTitle>
              {u.descripcion ? <CardDescription>{u.descripcion}</CardDescription> : null}
              <CardDescription>
                {u.integrantes} integrantes
                {u.encargados.length ? ` · Encargado: ${u.encargados.join(', ')}` : ''}
              </CardDescription>
              {u.mis_roles.length > 0 ? (
                <span className="flex flex-wrap gap-2">
                  {u.mis_roles.map((r) => (
                    <Badge key={r} tone="success">
                      {r}
                    </Badge>
                  ))}
                </span>
              ) : null}
            </CardLink>
          </li>
        ))}
      </ul>
    </div>
  )
}

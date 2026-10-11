import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Card, CardDescription, CardTitle, CheckboxField, PageHeader } from '@/design-system'
import { api } from '@/lib/api'
import { useCan, type User } from './use-auth'

interface Rol {
  clave: string
  nombre: string
  nivel: number
}

export function RolesPage() {
  const puede = useCan('roles.gestionar')
  const queryClient = useQueryClient()
  const roles = useQuery({ queryKey: ['roles'], queryFn: () => api<Rol[]>('/api/auth/roles/'), enabled: puede })
  const usuarios = useQuery({ queryKey: ['usuarios'], queryFn: () => api<User[]>('/api/auth/users/'), enabled: puede })

  const guardar = useMutation({
    mutationFn: ({ id, claves }: { id: number; claves: string[] }) =>
      api<User>(`/api/auth/users/${id}/roles/`, { method: 'POST', body: { roles: claves } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['usuarios'] }),
  })

  if (!puede) return <Alert tone="warning">No tienes permiso para asignar roles.</Alert>

  const alternar = (u: User, clave: string, activo: boolean) =>
    guardar.mutate({
      id: u.id,
      claves: activo ? [...u.roles, clave] : u.roles.filter((r) => r !== clave),
    })

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Roles" description="Asigna a cada persona los roles que le corresponden." module="admin" />
      {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
      {usuarios.data?.map((u) => (
        <Card key={u.id} className="flex flex-col gap-2">
          <CardTitle>{u.nombre}</CardTitle>
          <CardDescription>{u.whatsapp}</CardDescription>
          <div className="grid grid-cols-1 gap-x-4 md:grid-cols-3">
            {roles.data?.map((r) => (
              <CheckboxField
                key={r.clave}
                label={r.nombre}
                checked={u.roles.includes(r.clave)}
                disabled={guardar.isPending}
                onChange={(e) => alternar(u, r.clave, e.target.checked)}
              />
            ))}
          </div>
        </Card>
      ))}
    </div>
  )
}

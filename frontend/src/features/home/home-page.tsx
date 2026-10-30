import {
  Bell,
  Coins,
  HandHeart,
  UserCog,
  UserPlus,
  Users,
  UsersRound,
  type LucideIcon,
} from 'lucide-react'
import { Card, CardDescription, CardLink, CardTitle, PageHeader } from '@/design-system'
import { useAuth } from '@/features/auth/use-auth'
import { ResumenGrupos } from '@/features/grupos/dashboard-page'
import { InvitacionAvisos } from '@/features/notificaciones/notificaciones-card'

interface Acceso {
  to: string
  titulo: string
  detalle: string
  icono: LucideIcon
}

const ROLES_DE_SUPERVISION = ['lider', 'supervisor', 'pastor', 'anciano']

/** Pantalla de inicio: accesos rápidos según lo que la persona puede hacer y, si supervisa, el resumen. */
export function HomePage() {
  const { user } = useAuth()
  const can = (permiso: string) => !!user?.permisos.includes(permiso)
  const supervisa = !!user?.roles.some((r) => ROLES_DE_SUPERVISION.includes(r))

  const accesos: Acceso[] = [
    { to: '/grupos', titulo: 'Grupos', detalle: 'Pasar lista, estudio y reuniones.', icono: UsersRound },
    { to: '/peticiones', titulo: 'Peticiones', detalle: 'Motivos de oración.', icono: HandHeart },
    { to: '/avisos', titulo: 'Avisos', detalle: 'Mensajes de tus grupos.', icono: Bell },
    ...(can('ofrendas.acceso')
      ? [{ to: '/ofrendas', titulo: 'Ofrendas', detalle: 'Registro y aval.', icono: Coins }]
      : []),
    ...(can('personas.crear')
      ? [
          {
            to: '/personas/nueva',
            titulo: 'Registrar contacto',
            detalle: 'Alta rápida de una persona.',
            icono: UserPlus,
          },
        ]
      : []),
    ...(can('personas.ver')
      ? [{ to: '/personas', titulo: 'Personas', detalle: 'Expedientes y procesos.', icono: Users }]
      : []),
    { to: '/cuenta', titulo: 'Mi cuenta', detalle: 'Tu número, tu PIN y el color.', icono: UserCog },
  ]

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={user ? `Hola, ${user.nombre.split(' ')[0]}` : 'Bienvenido a MDF360'}
        description="Plataforma de gestión y discipulado de Mundo de Fe México."
        module="admin"
      />
      <InvitacionAvisos />
      <section aria-label="Accesos rápidos" className="flex flex-col gap-3">
        <h2 className="text-xl">Accesos rápidos</h2>
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {accesos.map(({ to, titulo, detalle, icono: Icono }) => (
            <li key={to}>
              <CardLink to={to} className="flex h-full items-center gap-4">
                <Icono aria-hidden className="size-8 shrink-0 text-primary" />
                <span className="flex flex-col">
                  <span className="font-bold">{titulo}</span>
                  <span className="text-sm text-muted-foreground">{detalle}</span>
                </span>
              </CardLink>
            </li>
          ))}
        </ul>
      </section>
      {supervisa ? (
        <section aria-label="Resumen de grupos">
          <ResumenGrupos />
        </section>
      ) : (
        <Card>
          <CardTitle>Tu semana</CardTitle>
          <CardDescription>
            Aquí verás el avance de tus grupos cuando tengas uno a tu cargo.
          </CardDescription>
        </Card>
      )}
    </div>
  )
}

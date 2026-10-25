import { Coins, Home, Palette, UsersRound, ScrollText, Settings, ShieldCheck, UserCog, UserPlus, Users } from 'lucide-react'
import { Outlet, Route, Routes } from 'react-router-dom'
import { AppShell, type NavItem } from '@/design-system'
import { AuditoriaPage } from '@/features/auditoria/auditoria-page'
import { ConfigPage } from '@/features/config/config-page'
import { AccountPage } from '@/features/auth/account-page'
import { ActivatePage } from '@/features/auth/activate-page'
import { InvitePage } from '@/features/auth/invite-page'
import { LoginPage } from '@/features/auth/login-page'
import { RecoveryPage } from '@/features/auth/recovery-page'
import { RequireAuth } from '@/features/auth/require-auth'
import { RolesPage } from '@/features/auth/roles-page'
import { useAuth } from '@/features/auth/use-auth'
import { DesignPage } from '@/features/design/design-page'
import { EstudiosPage } from '@/features/grupos/estudios-page'
import { ListaSinConexionPage } from '@/features/grupos/lista-sin-conexion-page'
import { GrupoPage } from '@/features/grupos/grupo-page'
import { GruposPage } from '@/features/grupos/grupos-page'
import { OfrendasPage } from '@/features/grupos/ofrendas-page'
import { ReunionPage } from '@/features/grupos/reunion-page'
import { SyncBanner } from '@/features/offline/sync-banner'
import { HomePage } from '@/features/home/home-page'
import { NuevaPersonaPage } from '@/features/personas/nueva-persona-page'
import { PersonaPage } from '@/features/personas/persona-page'
import { PersonasPage } from '@/features/personas/personas-page'

function PrivateLayout() {
  const { user } = useAuth()
  const can = (permiso: string) => !!user?.permisos.includes(permiso)
  const nav: NavItem[] = [
    { to: '/', label: 'Inicio', icon: Home },
    { to: '/grupos', label: 'Grupos', icon: UsersRound, module: 'grupos' as const },
    { to: '/ofrendas', label: 'Ofrendas', icon: Coins, module: 'grupos' as const },
    ...(can('personas.ver')
      ? [{ to: '/personas', label: 'Personas', icon: Users, module: 'admin' as const }]
      : []),
    ...(can('usuarios.invitar')
      ? [{ to: '/invitar', label: 'Invitar', icon: UserPlus, module: 'admin' as const }]
      : []),
    ...(can('roles.gestionar')
      ? [{ to: '/roles', label: 'Roles', icon: ShieldCheck, module: 'admin' as const }]
      : []),
    ...(can('bitacora.ver')
      ? [{ to: '/bitacora', label: 'Bitácora', icon: ScrollText, module: 'admin' as const }]
      : []),
    ...(can('config.gestionar')
      ? [{ to: '/configuracion', label: 'Configuración', icon: Settings, module: 'admin' as const }]
      : []),
    { to: '/cuenta', label: 'Mi cuenta', icon: UserCog },
    { to: '/diseno', label: 'Diseño', icon: Palette },
  ]
  return (
    <AppShell nav={nav}>
      <SyncBanner />
      <Outlet />
    </AppShell>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/activar/:token" element={<ActivatePage />} />
      <Route path="/recuperar" element={<RecoveryPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<PrivateLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/grupos" element={<GruposPage />} />
          <Route path="/grupos/reuniones/:rid" element={<ReunionPage />} />
          <Route path="/grupos/:id/hoy" element={<ListaSinConexionPage />} />
          <Route path="/grupos/:id" element={<GrupoPage />} />
          <Route path="/ofrendas" element={<OfrendasPage />} />
          <Route path="/estudios" element={<EstudiosPage />} />
          <Route path="/personas" element={<PersonasPage />} />
          <Route path="/personas/nueva" element={<NuevaPersonaPage />} />
          <Route path="/personas/:id" element={<PersonaPage />} />
          <Route path="/bitacora" element={<AuditoriaPage />} />
          <Route path="/configuracion" element={<ConfigPage />} />
          <Route path="/roles" element={<RolesPage />} />
          <Route path="/invitar" element={<InvitePage />} />
          <Route path="/cuenta" element={<AccountPage />} />
          <Route path="/diseno" element={<DesignPage />} />
        </Route>
      </Route>
    </Routes>
  )
}

import {
  Bell,
  Building2,
  Coins,
  HandHeart,
  Home,
  KeyRound,
  Palette,
  ScrollText,
  Settings,
  ShieldCheck,
  UserCog,
  UserPlus,
  Users,
  UsersRound,
} from 'lucide-react'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AppShell, type NavItem } from '@/design-system'
import { AuditoriaPage } from '@/features/auditoria/auditoria-page'
import { ConfigPage } from '@/features/config/config-page'
import { AccountPage } from '@/features/auth/account-page'
import { ActivatePage } from '@/features/auth/activate-page'
import { InvitePage } from '@/features/auth/invite-page'
import { LoginPage } from '@/features/auth/login-page'
import { RecoveryPage } from '@/features/auth/recovery-page'
import { RequireAuth } from '@/features/auth/require-auth'
import { UnidadPage } from '@/features/unidades/unidad-page'
import { UnidadesPage } from '@/features/unidades/unidades-page'
import { PermisosPage } from '@/features/auth/permisos-page'
import { RolesEquipoPage } from '@/features/equipos/roles-equipo-page'
import { RolesPage } from '@/features/auth/roles-page'
import { useAuth } from '@/features/auth/use-auth'
import { DesignPage } from '@/features/design/design-page'
import { UnirsePage } from '@/features/grupos/unirse-page'
import { EstudiosPage } from '@/features/grupos/estudios-page'
import { ListaSinConexionPage } from '@/features/grupos/lista-sin-conexion-page'
import { GrupoPage } from '@/features/grupos/grupo-page'
import { GruposPage } from '@/features/grupos/grupos-page'
import { AvisosPage } from '@/features/tablero/avisos-page'
import { OfrendasPage } from '@/features/grupos/ofrendas-page'
import { ReunionPage } from '@/features/grupos/reunion-page'
import { SyncBanner } from '@/features/offline/sync-banner'
import { FormularioPage } from '@/features/peticiones/formulario-page'
import { PeticionesPage } from '@/features/peticiones/peticiones-page'
import { HomePage } from '@/features/home/home-page'
import { NuevaPersonaPage } from '@/features/personas/nueva-persona-page'
import { PersonaPage } from '@/features/personas/persona-page'
import { PersonasPage } from '@/features/personas/personas-page'

function PrivateLayout() {
  const { user, logout } = useAuth()
  const can = (permiso: string) => !!user?.permisos.includes(permiso)
  const operacion = 'Operación'
  const catalogos = 'Catálogos'
  const administracion = 'Administración'
  const nav: NavItem[] = [
    { to: '/', label: 'Inicio', icon: Home },
    { to: '/grupos', label: 'Grupos', icon: UsersRound, module: 'grupos', group: operacion },
    { to: '/ministerios', label: 'Ministerios', icon: Building2, module: 'grupos', group: operacion },
    { to: '/peticiones', label: 'Peticiones', icon: HandHeart, module: 'grupos', group: operacion },
    { to: '/avisos', label: 'Avisos', icon: Bell, module: 'grupos', group: operacion },
    { to: '/ofrendas', label: 'Ofrendas', icon: Coins, module: 'grupos', group: operacion },
    ...(can('personas.ver')
      ? [{ to: '/personas', label: 'Personas', icon: Users, module: 'admin' as const, group: catalogos }]
      : []),
    ...(can('usuarios.invitar')
      ? [{ to: '/invitar', label: 'Invitar', icon: UserPlus, module: 'admin' as const, group: administracion }]
      : []),
    ...(can('roles.gestionar')
      ? [{ to: '/roles', label: 'Roles', icon: ShieldCheck, module: 'admin' as const, group: administracion }]
      : []),
    ...(can('roles.administrar')
      ? [{ to: '/permisos', label: 'Permisos', icon: KeyRound, module: 'admin' as const, group: administracion }]
      : []),
    ...(can('bitacora.ver')
      ? [{ to: '/bitacora', label: 'Bitácora', icon: ScrollText, module: 'admin' as const, group: administracion }]
      : []),
    ...(can('config.gestionar')
      ? [{ to: '/configuracion', label: 'Configuración', icon: Settings, module: 'admin' as const, group: administracion }]
      : []),
    // Catálogo interno del sistema de diseño: solo para quien administra el sistema
    ...(can('config.gestionar')
      ? [{ to: '/diseno', label: 'Diseño', icon: Palette, group: administracion }]
      : []),
    { to: '/cuenta', label: 'Mi cuenta', icon: UserCog },
  ]
  return (
    <AppShell nav={nav} userName={user?.nombre} onLogout={() => void logout()}>
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
      <Route path="/unirse/:token" element={<UnirsePage />} />
      <Route element={<RequireAuth />}>
        <Route element={<PrivateLayout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/grupos" element={<GruposPage />} />
          <Route path="/grupos/resumen" element={<Navigate to="/" replace />} />
          <Route path="/avisos" element={<AvisosPage />} />
          <Route path="/grupos/reuniones/:rid" element={<ReunionPage />} />
          <Route path="/grupos/:id/hoy" element={<ListaSinConexionPage />} />
          <Route path="/grupos/:id" element={<GrupoPage />} />
          <Route path="/ofrendas" element={<OfrendasPage />} />
          <Route path="/ministerios" element={<UnidadesPage />} />
          <Route path="/ministerios/:id" element={<UnidadPage />} />
          <Route path="/peticiones" element={<PeticionesPage />} />
          <Route path="/peticiones/formulario" element={<FormularioPage />} />
          <Route path="/estudios" element={<EstudiosPage />} />
          <Route path="/personas" element={<PersonasPage />} />
          <Route path="/personas/nueva" element={<NuevaPersonaPage />} />
          <Route path="/personas/:id" element={<PersonaPage />} />
          <Route path="/bitacora" element={<AuditoriaPage />} />
          <Route path="/configuracion" element={<ConfigPage />} />
          <Route path="/roles" element={<RolesPage />} />
          <Route path="/permisos" element={<PermisosPage />} />
          <Route path="/permisos/equipos" element={<RolesEquipoPage />} />
          <Route path="/invitar" element={<InvitePage />} />
          <Route path="/cuenta" element={<AccountPage />} />
          <Route path="/diseno" element={<DesignPage />} />
        </Route>
      </Route>
    </Routes>
  )
}

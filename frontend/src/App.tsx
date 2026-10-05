import { Home, Palette, UserCog, UserPlus } from 'lucide-react'
import { Outlet, Route, Routes } from 'react-router-dom'
import { AppShell, type NavItem } from '@/design-system'
import { AccountPage } from '@/features/auth/account-page'
import { ActivatePage } from '@/features/auth/activate-page'
import { InvitePage } from '@/features/auth/invite-page'
import { LoginPage } from '@/features/auth/login-page'
import { RecoveryPage } from '@/features/auth/recovery-page'
import { RequireAuth } from '@/features/auth/require-auth'
import { useAuth } from '@/features/auth/use-auth'
import { DesignPage } from '@/features/design/design-page'
import { HomePage } from '@/features/home/home-page'

function PrivateLayout() {
  const { user } = useAuth()
  const nav: NavItem[] = [
    { to: '/', label: 'Inicio', icon: Home },
    ...(user?.is_staff
      ? [{ to: '/invitar', label: 'Invitar', icon: UserPlus, module: 'admin' as const }]
      : []),
    { to: '/cuenta', label: 'Mi cuenta', icon: UserCog },
    { to: '/diseno', label: 'Diseño', icon: Palette },
  ]
  return (
    <AppShell nav={nav}>
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
          <Route path="/invitar" element={<InvitePage />} />
          <Route path="/cuenta" element={<AccountPage />} />
          <Route path="/diseno" element={<DesignPage />} />
        </Route>
      </Route>
    </Routes>
  )
}

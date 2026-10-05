import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './use-auth'

/** Protege las rutas privadas: sin sesión, manda a /login recordando a dónde iba. */
export function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <p className="p-8 text-center text-muted-foreground">Cargando…</p>
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

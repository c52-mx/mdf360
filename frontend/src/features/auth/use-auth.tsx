import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useContext, type ReactNode } from 'react'
import { api, ApiError } from '@/lib/api'

export interface User {
  id: number
  nombre: string
  whatsapp: string
  email: string
  requires_strong_credential: boolean
  roles: string[]
  permisos: string[]
}

interface AuthState {
  user: User | null
  loading: boolean
  setUser: (user: User | null) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

async function fetchMe(): Promise<User | null> {
  try {
    return await api<User>('/api/auth/me/')
  } catch (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null
    throw error
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const me = useQuery({ queryKey: ['me'], queryFn: fetchMe, retry: false, staleTime: Infinity })

  const setUser = (user: User | null) => queryClient.setQueryData(['me'], user)
  const logout = async () => {
    await api('/api/auth/logout/', { method: 'POST' })
    queryClient.clear()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user: me.data ?? null, loading: me.isPending, setUser, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useCan(permiso: string): boolean {
  const { user } = useAuth()
  return !!user?.permisos.includes(permiso)
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  return ctx
}

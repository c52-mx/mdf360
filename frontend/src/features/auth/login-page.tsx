import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Alert, AuthLayout, Button, Field } from '@/design-system'
import { api } from '@/lib/api'
import { useAuth, type User } from './use-auth'

export function LoginPage() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/'
  const [identifier, setIdentifier] = useState('')
  const [credential, setCredential] = useState('')

  const login = useMutation({
    mutationFn: () =>
      api<User>('/api/auth/login/', { method: 'POST', body: { identifier, credential } }),
    onSuccess: (loggedIn) => {
      setUser(loggedIn)
      navigate(from, { replace: true })
    },
  })

  if (user) return <Navigate to="/" replace />

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    login.mutate()
  }

  return (
    <AuthLayout title="Entrar" description="Usa tu número de WhatsApp o tu correo y tu PIN.">
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field
          label="WhatsApp o correo"
          autoComplete="username"
          inputMode="email"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          placeholder="5512345678"
          required
        />
        <Field
          label="PIN o contraseña"
          type="password"
          autoComplete="current-password"
          value={credential}
          onChange={(e) => setCredential(e.target.value)}
          required
        />
        {login.error ? <Alert tone="destructive">{login.error.message}</Alert> : null}
        <Button type="submit" size="lg" disabled={login.isPending}>
          {login.isPending ? 'Entrando…' : 'Entrar'}
        </Button>
      </form>
      <div className="flex flex-col gap-2">
        <Button asChild variant="ghost">
          <Link to="/recuperar">¿Olvidaste tu PIN?</Link>
        </Button>
        <Alert>Si es tu primera vez, entra con el enlace que te enviaron por WhatsApp.</Alert>
      </div>
    </AuthLayout>
  )
}

import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Alert, AuthLayout, Button, Field } from '@/design-system'
import { api } from '@/lib/api'
import { useAuth, type User } from './use-auth'

interface TokenInfo {
  nombre: string
  purpose: 'activation' | 'reset'
  requires_strong_credential: boolean
}

export function ActivatePage() {
  const { token = '' } = useParams()
  const { setUser } = useAuth()
  const navigate = useNavigate()
  const [credential, setCredential] = useState('')
  const [confirm, setConfirm] = useState('')
  const [mismatch, setMismatch] = useState(false)

  const info = useQuery({
    queryKey: ['activation', token],
    queryFn: () => api<TokenInfo>('/api/auth/activation/check/', { method: 'POST', body: { token } }),
    retry: false,
  })

  const complete = useMutation({
    mutationFn: () =>
      api<User>('/api/auth/activation/complete/', { method: 'POST', body: { token, credential } }),
    onSuccess: (user) => {
      setUser(user)
      navigate('/', { replace: true })
    },
  })

  if (info.isPending) {
    return <p className="p-8 text-center text-muted-foreground">Verificando enlace…</p>
  }
  if (info.isError) {
    return (
      <AuthLayout title="Enlace no válido">
        <Alert tone="destructive">{info.error.message}</Alert>
        <p>Pide a tu Líder que te envíe un enlace nuevo.</p>
        <Button asChild variant="outline">
          <Link to="/login">Ir a entrar</Link>
        </Button>
      </AuthLayout>
    )
  }

  const strong = info.data.requires_strong_credential
  const reset = info.data.purpose === 'reset'
  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (credential !== confirm) {
      setMismatch(true)
      return
    }
    setMismatch(false)
    complete.mutate()
  }

  return (
    <AuthLayout
      title={`Hola, ${info.data.nombre.split(' ')[0]}`}
      description={
        reset
          ? 'Elige tu nuevo acceso para volver a entrar.'
          : 'Elige tu acceso para activar tu cuenta.'
      }
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field
          label={strong ? 'Contraseña' : 'PIN'}
          type="password"
          autoComplete="new-password"
          inputMode={strong ? 'text' : 'numeric'}
          maxLength={strong ? 128 : 6}
          hint={
            strong
              ? 'Mínimo 10 caracteres, con letras y números.'
              : '6 números que puedas recordar. Evita 123456 o 111111.'
          }
          value={credential}
          onChange={(e) => setCredential(e.target.value)}
          required
        />
        <Field
          label={strong ? 'Repite la contraseña' : 'Repite el PIN'}
          type="password"
          autoComplete="new-password"
          inputMode={strong ? 'text' : 'numeric'}
          maxLength={strong ? 128 : 6}
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          error={mismatch ? 'No coinciden. Vuelve a escribirlos.' : undefined}
          required
        />
        {complete.error ? <Alert tone="destructive">{complete.error.message}</Alert> : null}
        <Button type="submit" size="lg" disabled={complete.isPending}>
          {complete.isPending ? 'Guardando…' : reset ? 'Guardar y entrar' : 'Activar mi cuenta'}
        </Button>
      </form>
    </AuthLayout>
  )
}

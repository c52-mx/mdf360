import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Alert, AuthLayout, Button, Field } from '@/design-system'
import { api } from '@/lib/api'

export function RecoveryPage() {
  const [identifier, setIdentifier] = useState('')
  const recover = useMutation({
    mutationFn: () =>
      api<{ detail: string }>('/api/auth/recovery/', { method: 'POST', body: { identifier } }),
  })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    recover.mutate()
  }

  return (
    <AuthLayout
      title="Recupera tu acceso"
      description="Si registraste un correo, te enviamos un enlace para elegir un PIN nuevo."
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field
          label="Tu correo"
          type="email"
          autoComplete="email"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          required
        />
        {recover.data ? <Alert tone="success">{recover.data.detail}</Alert> : null}
        {recover.error ? <Alert tone="destructive">{recover.error.message}</Alert> : null}
        <Button type="submit" size="lg" disabled={recover.isPending}>
          {recover.isPending ? 'Enviando…' : 'Enviar enlace'}
        </Button>
      </form>
      <Alert>¿No tienes correo? Pide a tu Líder que reinicie tu acceso.</Alert>
      <Button asChild variant="ghost">
        <Link to="/login">Volver a entrar</Link>
      </Button>
    </AuthLayout>
  )
}

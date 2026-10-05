import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Alert, Button, Card, CardDescription, CardTitle, Field, PageHeader } from '@/design-system'
import { api } from '@/lib/api'
import { useAuth, type User } from './use-auth'

export function AccountPage() {
  const { user, setUser, logout } = useAuth()
  const [whatsapp, setWhatsapp] = useState('')
  const [credential, setCredential] = useState('')

  const change = useMutation({
    mutationFn: () =>
      api<User>('/api/auth/me/whatsapp/', { method: 'POST', body: { whatsapp, credential } }),
    onSuccess: (updated) => {
      setUser(updated)
      setWhatsapp('')
      setCredential('')
    },
  })

  if (!user) return null

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    change.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Mi cuenta" description={user.nombre} module="admin" />

      <Card className="flex flex-col gap-1">
        <CardTitle>Mis datos de acceso</CardTitle>
        <CardDescription>WhatsApp: {user.whatsapp}</CardDescription>
        <CardDescription>Correo: {user.email || 'Sin correo registrado'}</CardDescription>
      </Card>

      <Card>
        <form onSubmit={onSubmit} className="flex max-w-md flex-col gap-4">
          <CardTitle>Cambiar mi número de WhatsApp</CardTitle>
          <Field
            label="Número nuevo"
            inputMode="tel"
            value={whatsapp}
            onChange={(e) => setWhatsapp(e.target.value)}
            required
          />
          <Field
            label="Tu PIN actual"
            type="password"
            hint="Lo pedimos para confirmar que eres tú."
            value={credential}
            onChange={(e) => setCredential(e.target.value)}
            required
          />
          {change.isSuccess ? <Alert tone="success">Tu número se actualizó.</Alert> : null}
          {change.error ? <Alert tone="destructive">{change.error.message}</Alert> : null}
          <Button type="submit" disabled={change.isPending}>
            Guardar número
          </Button>
        </form>
      </Card>

      <div>
        <Button variant="outline" onClick={() => void logout()}>
          Cerrar sesión
        </Button>
      </div>
    </div>
  )
}

import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Alert, Button, Card, CardDescription, CardTitle, Field, PageHeader } from '@/design-system'
import { api } from '@/lib/api'
import { useAuth, type User } from './use-auth'

interface Invitation {
  user: User
  activation_url: string
  whatsapp_url: string
  expires_at: string
}

export function InvitePage() {
  const { user } = useAuth()
  const [nombre, setNombre] = useState('')
  const [whatsapp, setWhatsapp] = useState('')
  const [email, setEmail] = useState('')
  const [copied, setCopied] = useState(false)

  const invite = useMutation({
    mutationFn: () =>
      api<Invitation>('/api/auth/invitations/', { method: 'POST', body: { nombre, whatsapp, email } }),
    onSuccess: () => setCopied(false),
  })

  if (!user?.is_staff) {
    return <Alert tone="warning">No tienes permiso para invitar personas.</Alert>
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    invite.mutate()
  }
  const copy = async (url: string) => {
    await navigator.clipboard.writeText(url)
    setCopied(true)
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Invitar a una persona"
        description="Crea su cuenta y envíale el enlace de activación por WhatsApp (sin costo)."
        module="admin"
      />
      <Card>
        <form onSubmit={onSubmit} className="flex max-w-md flex-col gap-4">
          <Field label="Nombre completo" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
          <Field
            label="Número de WhatsApp"
            inputMode="tel"
            value={whatsapp}
            onChange={(e) => setWhatsapp(e.target.value)}
            required
          />
          <Field
            label="Correo (opcional)"
            type="email"
            hint="Sirve para recuperar el acceso sin pedir ayuda."
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          {invite.error ? <Alert tone="destructive">{invite.error.message}</Alert> : null}
          <Button type="submit" disabled={invite.isPending}>
            Crear invitación
          </Button>
        </form>
      </Card>

      {invite.data ? (
        <Card className="flex flex-col gap-3">
          <CardTitle>Invitación lista para {invite.data.user.nombre}</CardTitle>
          <CardDescription>
            El enlace es de un solo uso y caduca el{' '}
            {new Date(invite.data.expires_at).toLocaleString('es-MX')}.
          </CardDescription>
          <div className="flex flex-wrap gap-3">
            <Button asChild variant="success">
              <a href={invite.data.whatsapp_url} target="_blank" rel="noreferrer">
                Enviar por WhatsApp
              </a>
            </Button>
            <Button variant="outline" onClick={() => void copy(invite.data.activation_url)}>
              {copied ? 'Enlace copiado' : 'Copiar enlace'}
            </Button>
          </div>
        </Card>
      ) : null}
    </div>
  )
}

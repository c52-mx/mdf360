import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert, Button, Card, CardDescription, CardTitle, Field, PageHeader, TextareaField } from '@/design-system'
import { api } from '@/lib/api'
import { useCan } from './use-auth'

interface Aviso {
  version: string
  texto: string
}

/** Quien administra la configuración publica aquí el aviso oficial cuando la iglesia lo tenga. */
export function AvisoPrivacidadPage() {
  const puede = useCan('config.gestionar')
  const queryClient = useQueryClient()
  const [version, setVersion] = useState('')
  const [texto, setTexto] = useState('')

  const vigente = useQuery({
    queryKey: ['aviso-privacidad'],
    queryFn: () => api<Aviso>('/api/personas/aviso-privacidad/'),
  })
  const publicar = useMutation({
    mutationFn: () => api<Aviso>('/api/personas/aviso-privacidad/publicar/', { method: 'POST', body: { version, texto } }),
    onSuccess: () => {
      setVersion('')
      setTexto('')
      void queryClient.invalidateQueries({ queryKey: ['aviso-privacidad'] })
      void queryClient.invalidateQueries({ queryKey: ['mi-perfil'] })
    },
  })

  if (!puede) return <Alert tone="warning">No tienes permiso para cambiar el aviso de privacidad.</Alert>

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Aviso de privacidad"
        description="El texto que aceptan las personas al registrarse. Al publicar una versión nueva, todas deberán aceptarla."
        module="admin"
      />
      <Card className="flex flex-col gap-3">
        <CardTitle>Texto vigente{vigente.data ? ` (versión ${vigente.data.version})` : ''}</CardTitle>
        {vigente.data?.version.includes('provisional') ? (
          <Alert tone="warning">
            Este texto es provisional. Reemplázalo por el aviso oficial que entregue el asesor legal antes de abrir
            el sistema a más personas.
          </Alert>
        ) : null}
        {vigente.isError ? <Alert tone="destructive">{vigente.error.message}</Alert> : null}
        <p className="whitespace-pre-line">{vigente.data?.texto}</p>
      </Card>

      <Card>
        <form
          className="flex max-w-3xl flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault()
            publicar.mutate()
          }}
        >
          <CardTitle>Publicar una versión nueva</CardTitle>
          <CardDescription>
            Pega el texto oficial y ponle una versión que no se haya usado (por ejemplo 1.0 o 2026-11). Cada
            consentimiento queda ligado a la versión que la persona aceptó.
          </CardDescription>
          <Field label="Versión" value={version} onChange={(e) => setVersion(e.target.value)} required />
          <TextareaField label="Texto del aviso" rows={14} value={texto} onChange={(e) => setTexto(e.target.value)} required />
          {publicar.isSuccess ? <Alert tone="success">El aviso nuevo ya está vigente.</Alert> : null}
          {publicar.error ? <Alert tone="destructive">{publicar.error.message}</Alert> : null}
          <div>
            <Button type="submit" disabled={publicar.isPending}>
              Publicar aviso
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}

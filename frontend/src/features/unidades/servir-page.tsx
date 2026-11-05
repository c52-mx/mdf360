import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { Alert, AuthLayout, Button, CardDescription, CheckboxField, Field } from '@/design-system'
import { api } from '@/lib/api'

interface InfoMinisterio {
  ministerio: string
  descripcion: string
}

/** Pantalla pública a la que llega quien escanea el QR de un ministerio: entra sin aprobación. */
export function ServirPage() {
  const { token = '' } = useParams()
  const [nombre, setNombre] = useState('')
  const [whatsapp, setWhatsapp] = useState('')
  const [acepta, setAcepta] = useState(false)

  const info = useQuery({
    queryKey: ['servir', token],
    queryFn: () => api<InfoMinisterio>(`/api/unidades/enlace/${token}/`),
    retry: false,
  })
  const aviso = useQuery({
    queryKey: ['aviso-privacidad'],
    queryFn: () => api<{ version: string; texto: string }>('/api/personas/aviso-privacidad/'),
    staleTime: Infinity,
  })
  const sumarse = useMutation({
    mutationFn: () =>
      api(`/api/unidades/enlace/${token}/sumarse/`, {
        method: 'POST',
        body: { nombre, whatsapp, acepta_datos: acepta },
      }),
  })

  if (info.isPending) {
    return (
      <AuthLayout title="Servir en un ministerio">
        <CardDescription>Cargando…</CardDescription>
      </AuthLayout>
    )
  }
  if (info.isError) {
    return (
      <AuthLayout title="Enlace no válido">
        <Alert tone="warning">Este enlace ya no sirve. Pide a tu encargado que te comparta uno nuevo.</Alert>
      </AuthLayout>
    )
  }
  const { ministerio, descripcion } = info.data

  if (sumarse.isSuccess) {
    return (
      <AuthLayout title={ministerio}>
        <Alert tone="success">
          ¡Listo! Ya eres parte de {ministerio}. Tu encargado te dará los siguientes pasos.
        </Alert>
      </AuthLayout>
    )
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    sumarse.mutate()
  }

  return (
    <AuthLayout
      title={`Servir en ${ministerio}`}
      description={descripcion || 'Déjanos tus datos y quedas dentro del equipo.'}
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field label="Tu nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
        <Field
          label="Tu WhatsApp"
          inputMode="tel"
          value={whatsapp}
          onChange={(e) => setWhatsapp(e.target.value)}
          required
        />
        {aviso.data ? (
          <details>
            <summary className="cursor-pointer font-semibold text-primary">Leer el aviso de privacidad</summary>
            <p className="mt-2 whitespace-pre-line text-sm text-muted-foreground">{aviso.data.texto}</p>
          </details>
        ) : null}
        <CheckboxField
          checked={acepta}
          onChange={(e) => setAcepta(e.target.checked)}
          label="Acepto el aviso de privacidad"
        />
        {sumarse.error ? <Alert tone="destructive">{sumarse.error.message}</Alert> : null}
        <Button type="submit" disabled={!acepta || sumarse.isPending}>
          Sumarme al equipo
        </Button>
      </form>
    </AuthLayout>
  )
}

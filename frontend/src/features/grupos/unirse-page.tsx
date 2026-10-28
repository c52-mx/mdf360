import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { Alert, AuthLayout, Button, CardDescription, CheckboxField, Field } from '@/design-system'
import { api } from '@/lib/api'

interface InfoGrupo {
  grupo: string
  dia: string
  hora: string
}
interface Solicitud {
  codigo: string
  estado: Estado
  grupo: string
}
type Estado = 'pendiente' | 'aprobada' | 'rechazada'

const clave = (token: string) => `mdf360.solicitud.${token}`

function codigoGuardado(token: string): string | null {
  try {
    return localStorage.getItem(clave(token))
  } catch {
    return null
  }
}
function guardarCodigo(token: string, codigo: string) {
  try {
    localStorage.setItem(clave(token), codigo)
  } catch {
    // sin almacenamiento: al recargar tendrá que volver a pedir su ingreso
  }
}

/** Pantalla pública a la que llega quien abre el enlace o escanea el QR de un grupo. */
export function UnirsePage() {
  const { token = '' } = useParams()
  const [nombre, setNombre] = useState('')
  const [whatsapp, setWhatsapp] = useState('')
  const [acepta, setAcepta] = useState(false)
  const [codigo, setCodigo] = useState<string | null>(() => codigoGuardado(token))

  const info = useQuery({
    queryKey: ['unirse', token],
    queryFn: () => api<InfoGrupo>(`/api/grupos/enlace/${token}/`),
    retry: false,
  })
  const aviso = useQuery({
    queryKey: ['aviso-privacidad'],
    queryFn: () => api<{ version: string; texto: string }>('/api/personas/aviso-privacidad/'),
    staleTime: Infinity,
  })

  const solicitar = useMutation({
    mutationFn: () =>
      api<Solicitud>(`/api/grupos/enlace/${token}/solicitar/`, {
        method: 'POST',
        body: { nombre, whatsapp, acepta_datos: acepta },
      }),
    onSuccess: (s) => {
      guardarCodigo(token, s.codigo)
      setCodigo(s.codigo)
    },
  })

  // Sala de espera: se consulta cada pocos segundos hasta que el líder resuelve
  const espera = useQuery({
    queryKey: ['sala-de-espera', codigo],
    enabled: codigo !== null,
    queryFn: () => api<{ estado: Estado; grupo: string }>(`/api/grupos/solicitudes/${codigo}/`),
    refetchInterval: (q) => (q.state.data?.estado === 'pendiente' || !q.state.data ? 4000 : false),
    retry: false,
  })

  if (info.isPending) {
    return (
      <AuthLayout title="Unirte a un grupo">
        <CardDescription>Cargando…</CardDescription>
      </AuthLayout>
    )
  }
  if (info.isError) {
    return (
      <AuthLayout title="Enlace no válido">
        <Alert tone="warning">
          Este enlace ya no sirve. Pide a tu líder que te comparta uno nuevo.
        </Alert>
      </AuthLayout>
    )
  }
  const grupo = info.data
  const horario = [grupo.dia, grupo.hora].filter(Boolean).join(' ')

  if (codigo !== null && espera.data) {
    const { estado } = espera.data
    return (
      <AuthLayout title={grupo.grupo} description={horario || undefined}>
        {estado === 'pendiente' ? (
          <Alert tone="warning">
            Tu solicitud llegó. Espera a que tu líder te apruebe; esta pantalla se actualiza sola.
          </Alert>
        ) : estado === 'aprobada' ? (
          <Alert tone="success">¡Listo! Ya eres parte de {grupo.grupo}. Te esperamos en la próxima reunión.</Alert>
        ) : (
          <Alert tone="destructive">
            Tu solicitud no fue aprobada. Si crees que fue un error, habla con tu líder.
          </Alert>
        )}
      </AuthLayout>
    )
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    solicitar.mutate()
  }

  return (
    <AuthLayout
      title={`Unirte a ${grupo.grupo}`}
      description={`${horario ? `${horario}. ` : ''}Déjanos tus datos y tu líder aprobará tu ingreso.`}
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
        {solicitar.error ? <Alert tone="destructive">{solicitar.error.message}</Alert> : null}
        <Button type="submit" disabled={!acepta || solicitar.isPending}>
          Pedir mi ingreso
        </Button>
      </form>
    </AuthLayout>
  )
}

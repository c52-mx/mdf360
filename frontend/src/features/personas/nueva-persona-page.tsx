import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Alert,
  Button,
  Card,
  CheckboxField,
  Field,
  PageHeader,
  SelectField,
} from '@/design-system'
import { api, ApiError } from '@/lib/api'
import { procedenciaOptions, type Persona, type Procedencia } from './types'

interface Aviso {
  version: string
  texto: string
}

export function NuevaPersonaPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [nombre, setNombre] = useState('')
  const [apellidoPaterno, setApellidoPaterno] = useState('')
  const [whatsapp, setWhatsapp] = useState('')
  const [procedencia, setProcedencia] = useState<Procedencia>('visitante')
  const [aceptaDatos, setAceptaDatos] = useState(false)
  const [aceptaFoto, setAceptaFoto] = useState(false)

  const aviso = useQuery({
    queryKey: ['aviso-privacidad'],
    queryFn: () => api<Aviso>('/api/personas/aviso-privacidad/'),
    staleTime: Infinity,
  })

  const crear = useMutation({
    mutationFn: () =>
      api<Persona>('/api/personas/', {
        method: 'POST',
        body: {
          nombre,
          apellido_paterno: apellidoPaterno,
          whatsapp,
          procedencia,
          acepta_datos: aceptaDatos,
          acepta_foto: aceptaFoto,
        },
      }),
    onSuccess: (persona) => {
      void queryClient.invalidateQueries({ queryKey: ['personas'] })
      navigate(`/personas/${persona.id}`)
    },
  })

  const duplicado = crear.error instanceof ApiError && crear.error.code === 'duplicate'
  const duplicadoId =
    crear.error instanceof ApiError ? (crear.error.data.persona_id as number | undefined) : undefined

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    crear.mutate()
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Nuevo contacto"
        description="Registro breve: nombre y WhatsApp. El expediente completo se llena después."
        module="admin"
      />
      <Card>
        <form onSubmit={onSubmit} className="flex max-w-xl flex-col gap-4">
          <Field label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} required />
          <Field
            label="Apellido paterno (opcional)"
            value={apellidoPaterno}
            onChange={(e) => setApellidoPaterno(e.target.value)}
          />
          <Field
            label="Número de WhatsApp"
            inputMode="tel"
            hint="10 dígitos. Sirve para darle seguimiento y evitar registros duplicados."
            value={whatsapp}
            onChange={(e) => setWhatsapp(e.target.value)}
            required
          />
          <SelectField
            label="¿De dónde viene?"
            value={procedencia}
            onChange={(e) => setProcedencia(e.target.value as Procedencia)}
            options={procedenciaOptions}
          />

          <details className="rounded-control border border-border p-3">
            <summary className="cursor-pointer font-bold">Leer el aviso de privacidad</summary>
            <p className="mt-3 whitespace-pre-line text-sm text-muted-foreground">
              {aviso.data?.texto ?? 'Cargando aviso…'}
            </p>
          </details>
          <CheckboxField
            checked={aceptaDatos}
            onChange={(e) => setAceptaDatos(e.target.checked)}
            label="La persona acepta el aviso de privacidad"
          />
          <CheckboxField
            checked={aceptaFoto}
            onChange={(e) => setAceptaFoto(e.target.checked)}
            label="La persona autoriza el uso de su fotografía (opcional)"
          />

          {duplicado ? (
            <Alert tone="warning">
              {crear.error?.message}{' '}
              {duplicadoId ? (
                <Link className="underline" to={`/personas/${duplicadoId}`}>
                  Abrir su registro
                </Link>
              ) : null}
            </Alert>
          ) : crear.error ? (
            <Alert tone="destructive">{crear.error.message}</Alert>
          ) : null}

          <Button type="submit" size="lg" disabled={crear.isPending || !aceptaDatos}>
            {crear.isPending ? 'Guardando…' : 'Guardar contacto'}
          </Button>
        </form>
      </Card>
    </div>
  )
}

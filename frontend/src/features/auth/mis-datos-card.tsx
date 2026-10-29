import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import {
  Alert,
  Avatar,
  Button,
  Card,
  CardDescription,
  CardTitle,
  CheckboxField,
  Field,
  FileButton,
} from '@/design-system'
import { api, apiForm } from '@/lib/api'
import { useAuth } from './use-auth'

interface Perfil {
  nombre: string
  apellido_paterno: string
  apellido_materno: string
  fecha_nacimiento: string | null
  telefono_fijo: string
  calle_numero: string
  colonia: string
  codigo_postal: string
  alcaldia: string
  devocional_personal: string
  oracion_familias: boolean
  oracion_familias_detalle: string
  nombre_completo: string
  tiene_foto: boolean
  acepto_foto: boolean
}

type Borrador = Omit<Perfil, 'nombre_completo' | 'tiene_foto' | 'acepto_foto'>

const CAMPOS: (keyof Borrador)[] = [
  'nombre',
  'apellido_paterno',
  'apellido_materno',
  'fecha_nacimiento',
  'telefono_fijo',
  'calle_numero',
  'colonia',
  'codigo_postal',
  'alcaldia',
  'devocional_personal',
  'oracion_familias',
  'oracion_familias_detalle',
]

/** Los datos básicos que la propia persona corrige. Nada de esto cambia su acceso ni su grupo. */
export function MisDatosCard() {
  const perfil = useQuery({ queryKey: ['mi-perfil'], queryFn: () => api<Perfil>('/api/personas/mi-perfil/') })
  if (perfil.isPending) return null
  if (perfil.isError) return <Alert tone="destructive">{perfil.error.message}</Alert>
  return <MisDatosForm p={perfil.data} />
}

function MisDatosForm({ p }: { p: Perfil }) {
  const queryClient = useQueryClient()
  const { user, setUser } = useAuth()
  const [form, setForm] = useState<Borrador>(
    () => Object.fromEntries(CAMPOS.map((c) => [c, p[c]])) as unknown as Borrador,
  )
  const [aceptaFoto, setAceptaFoto] = useState(false)
  const [version, setVersion] = useState(0)

  const guardar = useMutation({
    mutationFn: () => api<Perfil>('/api/personas/mi-perfil/', { method: 'PATCH', body: form }),
    onSuccess: (nuevo) => {
      queryClient.setQueryData(['mi-perfil'], nuevo)
      if (user) setUser({ ...user, nombre: nuevo.nombre_completo })
    },
  })
  const subirFoto = useMutation({
    mutationFn: (archivo: File) => {
      const datos = new FormData()
      datos.append('foto', archivo)
      datos.append('acepta_foto', String(aceptaFoto))
      return apiForm<Perfil>('/api/personas/mi-perfil/foto/', datos)
    },
    onSuccess: (nuevo) => {
      queryClient.setQueryData(['mi-perfil'], nuevo)
      setVersion((v) => v + 1)
    },
  })

  const poner = <K extends keyof Borrador>(campo: K, valor: Borrador[K]) => setForm({ ...form, [campo]: valor })
  const texto = (campo: keyof Borrador) => (form[campo] as string | null) ?? ''
  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    guardar.mutate()
  }

  return (
    <Card className="flex flex-col gap-4">
      <CardTitle>Mis datos</CardTitle>
      <CardDescription>
        Corrige tu nombre, tu domicilio y tus datos básicos. Tu número, tu correo, tu grupo y tus
        responsabilidades los administra la iglesia.
      </CardDescription>

      <div className="flex flex-wrap items-center gap-4">
        <Avatar
          name={p.nombre_completo}
          src={p.tiene_foto ? `/api/personas/mi-perfil/foto/?v=${version}` : undefined}
          size="lg"
        />
        <div className="flex flex-col gap-2">
          {!p.acepto_foto ? (
            <CheckboxField
              checked={aceptaFoto}
              onChange={(e) => setAceptaFoto(e.target.checked)}
              label="Acepto que mi fotografía se use para identificarme dentro del sistema"
            />
          ) : null}
          <div>
            <FileButton onFile={(f) => subirFoto.mutate(f)} disabled={subirFoto.isPending || (!p.acepto_foto && !aceptaFoto)}>
              {p.tiene_foto ? 'Cambiar mi foto' : 'Subir mi foto'}
            </FileButton>
          </div>
        </div>
      </div>
      {subirFoto.error ? <Alert tone="destructive">{subirFoto.error.message}</Alert> : null}

      <form onSubmit={onSubmit} className="grid max-w-3xl grid-cols-1 gap-4 md:grid-cols-2">
        <Field label="Nombre(s)" value={texto('nombre')} onChange={(e) => poner('nombre', e.target.value)} required />
        <Field
          label="Apellido paterno"
          value={texto('apellido_paterno')}
          onChange={(e) => poner('apellido_paterno', e.target.value)}
        />
        <Field
          label="Apellido materno"
          value={texto('apellido_materno')}
          onChange={(e) => poner('apellido_materno', e.target.value)}
        />
        <Field
          label="Fecha de nacimiento"
          type="date"
          value={texto('fecha_nacimiento')}
          onChange={(e) => poner('fecha_nacimiento', e.target.value || null)}
        />
        <Field
          label="Teléfono fijo"
          inputMode="tel"
          value={texto('telefono_fijo')}
          onChange={(e) => poner('telefono_fijo', e.target.value)}
        />
        <Field
          label="Calle y número"
          value={texto('calle_numero')}
          onChange={(e) => poner('calle_numero', e.target.value)}
        />
        <Field label="Colonia" value={texto('colonia')} onChange={(e) => poner('colonia', e.target.value)} />
        <Field
          label="Código postal"
          inputMode="numeric"
          value={texto('codigo_postal')}
          onChange={(e) => poner('codigo_postal', e.target.value)}
        />
        <Field
          label="Alcaldía o municipio"
          value={texto('alcaldia')}
          onChange={(e) => poner('alcaldia', e.target.value)}
        />
        <Field
          label="Mi devocional personal"
          value={texto('devocional_personal')}
          onChange={(e) => poner('devocional_personal', e.target.value)}
        />
        <div className="md:col-span-2">
          <CheckboxField
            checked={form.oracion_familias}
            onChange={(e) => poner('oracion_familias', e.target.checked)}
            label="Participo en la Oración de Familias en Acción (miércoles)"
          />
        </div>
        {form.oracion_familias ? (
          <div className="md:col-span-2">
            <Field
              label="Detalle de la oración de familias"
              value={texto('oracion_familias_detalle')}
              onChange={(e) => poner('oracion_familias_detalle', e.target.value)}
            />
          </div>
        ) : null}
        <div className="flex flex-col gap-3 md:col-span-2">
          {guardar.isSuccess ? <Alert tone="success">Tus datos se guardaron.</Alert> : null}
          {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
          <div>
            <Button type="submit" disabled={guardar.isPending}>
              Guardar mis datos
            </Button>
          </div>
        </div>
      </form>
    </Card>
  )
}

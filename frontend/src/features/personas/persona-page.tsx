import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type ChangeEvent, type FormEvent } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  CheckboxField,
  Field,
  FileButton,
  PageHeader,
  Section,
  SelectField,
  TextareaField,
} from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api, apiUpload } from '@/lib/api'
import {
  fotoUrl,
  nivelAyuda,
  nivelLabel,
  procedenciaOptions,
  type Movimiento,
  type Persona,
  type Procedencia,
  type ProcesoFila,
} from './types'

const hoy = () => new Date().toISOString().slice(0, 10)

type Form = Omit<Persona, 'faltantes_edu' | 'procesos'> & { procesos: ProcesoFila[] }

export function PersonaPage() {
  const { id = '' } = useParams()
  const persona = useQuery({
    queryKey: ['persona', id],
    queryFn: () => api<Persona>(`/api/personas/${id}/`),
  })

  if (persona.isPending) return <p className="text-muted-foreground">Cargando…</p>
  if (persona.isError) return <Alert tone="destructive">{persona.error.message}</Alert>
  // La clave reinicia el formulario cuando el servidor devuelve datos nuevos.
  return <Ficha key={`${persona.data.id}-${persona.data.actualizado_en}`} persona={persona.data} />
}

function Ficha({ persona }: { persona: Persona }) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<Form>(persona)
  const [bajaAbierta, setBajaAbierta] = useState(false)
  const [bajaFecha, setBajaFecha] = useState(hoy())
  const [bajaMotivo, setBajaMotivo] = useState('')
  const puedeAsignar = useCan('grupos.gestionar')
  const [grupoElegido, setGrupoElegido] = useState('')
  const [trasladoAbierto, setTrasladoAbierto] = useState(false)
  const [trasladoFecha, setTrasladoFecha] = useState(hoy())
  const [trasladoIglesia, setTrasladoIglesia] = useState('')
  const [trasladoMotivo, setTrasladoMotivo] = useState('')

  const refrescar = (actualizada: Persona) => {
    queryClient.setQueryData(['persona', String(actualizada.id)], actualizada)
    void queryClient.invalidateQueries({ queryKey: ['personas'] })
    void queryClient.invalidateQueries({ queryKey: ['movimientos', actualizada.id] })
  }

  const movimientos = useQuery({
    queryKey: ['movimientos', persona.id],
    queryFn: () => api<Movimiento[]>(`/api/personas/${persona.id}/movimientos/`),
  })

  const texto = (campo: keyof Form) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [campo]: e.target.value }))
  const casilla = (campo: keyof Form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [campo]: e.target.checked }))
  const proceso = (indice: number, cambios: Partial<ProcesoFila>) =>
    setForm((f) => ({
      ...f,
      procesos: f.procesos.map((p, i) => (i === indice ? { ...p, ...cambios } : p)),
    }))

  const guardar = useMutation({
    mutationFn: async () => {
      await api<Persona>(`/api/personas/${persona.id}/`, {
        method: 'PATCH',
        body: {
          nombre: form.nombre,
          apellido_paterno: form.apellido_paterno,
          apellido_materno: form.apellido_materno,
          fecha_nacimiento: form.fecha_nacimiento || null,
          procedencia: form.procedencia,
          whatsapp: form.whatsapp,
          telefono_fijo: form.telefono_fijo,
          email: form.email,
          calle_numero: form.calle_numero,
          colonia: form.colonia,
          codigo_postal: form.codigo_postal,
          alcaldia: form.alcaldia,
          sector: form.sector,
          grupo_conexion: form.grupo_conexion,
          lider: form.lider,
          miembro_desde: form.miembro_desde || null,
          sirve_en_ministerio: form.sirve_en_ministerio,
          ministerios: form.ministerios,
          devocional_personal: form.devocional_personal,
          oracion_familias: form.oracion_familias,
          oracion_familias_detalle: form.oracion_familias_detalle,
          otros_cursos: form.otros_cursos,
          observaciones: form.observaciones,
        },
      })
      return api<Persona>(`/api/personas/${persona.id}/procesos/`, {
        method: 'POST',
        body: form.procesos.map((p) => ({
          proceso: p.proceso,
          completado: p.completado,
          fecha: p.fecha || null,
          maestro: p.maestro,
        })),
      })
    },
    onSuccess: refrescar,
  })

  const subirFoto = useMutation({
    mutationFn: (file: File) => apiUpload<Persona>(`/api/personas/${persona.id}/foto/`, 'foto', file),
    onSuccess: refrescar,
  })
  const subirNivel = useMutation({
    mutationFn: (nivel: 'participante' | 'edu') =>
      api<Persona>(`/api/personas/${persona.id}/nivel/`, { method: 'POST', body: { nivel } }),
    onSuccess: refrescar,
  })
  const darBaja = useMutation({
    mutationFn: () =>
      api<Persona>(`/api/personas/${persona.id}/baja/`, {
        method: 'POST',
        body: { fecha: bajaFecha, motivo: bajaMotivo },
      }),
    onSuccess: (actualizada) => {
      setBajaAbierta(false)
      refrescar(actualizada)
    },
  })
  const grupos = useQuery({
    queryKey: ['grupos', 'para-asignar'],
    enabled: puedeAsignar && persona.activo,
    queryFn: () => api<{ id: number; nombre: string; suspendido: boolean }[]>('/api/grupos/?estado=activos'),
  })
  const asignar = useMutation({
    mutationFn: () =>
      api(`/api/grupos/${grupoElegido}/integrantes/`, {
        method: 'POST',
        body: { whatsapp: persona.whatsapp, nombre: persona.nombre, rol: 'asistente', acepta_datos: false },
      }),
    onSuccess: async () => {
      setGrupoElegido('')
      const actualizada = await api<Persona>(`/api/personas/${persona.id}/`)
      refrescar(actualizada)
      void queryClient.invalidateQueries({ queryKey: ['grupos'] })
    },
  })
  const trasladar = useMutation({
    mutationFn: () =>
      api<Persona>(`/api/personas/${persona.id}/traslado/`, {
        method: 'POST',
        body: { fecha: trasladoFecha, iglesia_destino: trasladoIglesia, motivo: trasladoMotivo },
      }),
    onSuccess: (actualizada) => {
      setTrasladoAbierto(false)
      refrescar(actualizada)
    },
  })
  const reactivar = useMutation({
    mutationFn: () => api<Persona>(`/api/personas/${persona.id}/reactivar/`, { method: 'POST', body: {} }),
    onSuccess: refrescar,
  })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    guardar.mutate()
  }
  const siguienteNivel = persona.nivel === 'contacto' ? 'participante' : persona.nivel === 'participante' ? 'edu' : null
  const errorNivel =
    subirNivel.error ?? reactivar.error ?? darBaja.error ?? trasladar.error ?? asignar.error ?? subirFoto.error

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-6">
      <Link to="/personas" className="presionable flex w-fit items-center gap-2 font-semibold text-primary">
        <ArrowLeft aria-hidden className="size-5" />
        Volver al listado
      </Link>
      <PageHeader
        title={persona.nombre_completo}
        description={persona.edad !== null ? `${persona.edad} años` : undefined}
        module="admin"
        actions={
          <Button type="submit" disabled={guardar.isPending}>
            {guardar.isPending ? 'Guardando…' : 'Guardar cambios'}
          </Button>
        }
      />

      {guardar.isSuccess ? <Alert tone="success">Los cambios se guardaron.</Alert> : null}
      {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
      {errorNivel ? <Alert tone="destructive">{errorNivel.message}</Alert> : null}
      {!persona.activo ? <Alert tone="warning">Esta persona está dada de baja.</Alert> : null}

      <Card className="flex flex-wrap items-center gap-5">
        <Avatar name={persona.nombre_completo} src={fotoUrl(persona, persona.actualizado_en)} size="lg" />
        <div className="flex flex-1 flex-col gap-2">
          <div className="flex flex-wrap gap-2">
            <Badge tone="primary">{nivelLabel[persona.nivel]}</Badge>
            {persona.activo ? <Badge tone="success">Activo</Badge> : <Badge tone="warning">Baja</Badge>}
            {persona.roles.map((rol) => (
              <Badge key={rol} tone="neutral">
                {rol}
              </Badge>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <FileButton onFile={(file) => subirFoto.mutate(file)} disabled={subirFoto.isPending}>
              {persona.tiene_foto ? 'Cambiar foto' : 'Subir foto'}
            </FileButton>
          </div>
        </div>
      </Card>

      <Card className="flex flex-col gap-3">
        <CardTitle>Nivel de registro</CardTitle>
        <ul className="flex flex-col gap-2">
          {(['contacto', 'participante', 'edu'] as const).map((n) => (
            <li key={n} className="flex flex-wrap items-baseline gap-x-3">
              <Badge tone={n === persona.nivel ? 'primary' : 'neutral'}>{nivelLabel[n]}</Badge>
              <span className="text-muted-foreground">{nivelAyuda[n]}</span>
            </li>
          ))}
        </ul>
        {siguienteNivel ? (
          <div className="flex flex-col items-start gap-2">
            <Button type="button" variant="outline" onClick={() => subirNivel.mutate(siguienteNivel)}>
              {siguienteNivel === 'participante' ? 'Subir a participante' : 'Completar expediente (EDU)'}
            </Button>
            {siguienteNivel === 'edu' && persona.faltantes_edu.length > 0 ? (
              <CardDescription>Para el expediente completo falta: {persona.faltantes_edu.join(', ')}.</CardDescription>
            ) : null}
          </div>
        ) : null}
      </Card>

      <Card className="flex flex-col gap-3">
        <CardTitle>Grupos</CardTitle>
        {persona.grupos.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {persona.grupos.map((g) => (
              <Badge key={g} tone="success">
                {g}
              </Badge>
            ))}
          </div>
        ) : (
          <CardDescription>No pertenece a ningún grupo.</CardDescription>
        )}
        {puedeAsignar && persona.activo && persona.whatsapp ? (
          <div className="flex max-w-xl flex-wrap items-end gap-3">
            <div className="min-w-48 flex-1">
              <SelectField
                label="Asignar a un grupo"
                value={grupoElegido}
                onChange={(e) => setGrupoElegido(e.target.value)}
                options={[
                  { value: '', label: 'Elige un grupo' },
                  ...(grupos.data ?? [])
                    .filter((g) => !persona.grupos.includes(g.nombre))
                    .map((g) => ({ value: String(g.id), label: g.nombre })),
                ]}
              />
            </div>
            <Button type="button" disabled={!grupoElegido || asignar.isPending} onClick={() => asignar.mutate()}>
              Asignar
            </Button>
          </div>
        ) : null}
        {puedeAsignar && persona.activo && !persona.whatsapp ? (
          <CardDescription>Para asignarla a un grupo registra primero su WhatsApp.</CardDescription>
        ) : null}
        {puedeAsignar ? (
          <CardDescription>El líder del grupo y la persona (si tiene cuenta) reciben un aviso.</CardDescription>
        ) : null}
      </Card>

      {persona.vehiculos.length > 0 ? (
        <Card className="flex flex-col gap-2">
          <CardTitle>Vehículos</CardTitle>
          <ul className="flex flex-col gap-1">
            {persona.vehiculos.map((v) => (
              <li key={v.id}>
                {v.descripcion}
                {v.color ? `, ${v.color}` : ''}
                {v.placas ? ` · placas ${v.placas}` : ''}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <Card className="flex flex-col gap-4">
        <CardTitle>Situación en la iglesia</CardTitle>
        {persona.activo ? (
          bajaAbierta ? (
            <div className="grid max-w-xl grid-cols-1 gap-4">
              <CardDescription>
                La persona sale de sus grupos y su acceso a la aplicación queda inactivo. Su historial se conserva y, al reactivarla, todo regresa.
              </CardDescription>
              <Field label="Fecha" type="date" value={bajaFecha} onChange={(e) => setBajaFecha(e.target.value)} />
              <Field label="Motivo" value={bajaMotivo} onChange={(e) => setBajaMotivo(e.target.value)} />
              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="destructive"
                  disabled={!bajaMotivo.trim() || darBaja.isPending}
                  onClick={() => darBaja.mutate()}
                >
                  Confirmar baja
                </Button>
                <Button type="button" variant="ghost" onClick={() => setBajaAbierta(false)}>
                  Cancelar
                </Button>
              </div>
            </div>
          ) : trasladoAbierto ? (
            <div className="grid max-w-xl grid-cols-1 gap-4">
              <CardDescription>
                La persona queda inactiva con la iglesia de destino en su historial, sale de sus grupos y su acceso queda inactivo.
              </CardDescription>
              <Field label="Fecha" type="date" value={trasladoFecha} onChange={(e) => setTrasladoFecha(e.target.value)} />
              <Field
                label="Iglesia a la que se traslada"
                value={trasladoIglesia}
                onChange={(e) => setTrasladoIglesia(e.target.value)}
              />
              <Field label="Motivo (opcional)" value={trasladoMotivo} onChange={(e) => setTrasladoMotivo(e.target.value)} />
              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="destructive"
                  disabled={!trasladoIglesia.trim() || trasladar.isPending}
                  onClick={() => trasladar.mutate()}
                >
                  Confirmar traslado
                </Button>
                <Button type="button" variant="ghost" onClick={() => setTrasladoAbierto(false)}>
                  Cancelar
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap gap-3">
              <Button type="button" variant="outline" onClick={() => setTrasladoAbierto(true)}>
                Pasar a otra iglesia
              </Button>
              <Button type="button" variant="outline" onClick={() => setBajaAbierta(true)}>
                Dar de baja
              </Button>
            </div>
          )
        ) : (
          <div>
            <Button type="button" variant="success" onClick={() => reactivar.mutate()}>
              Reactivar
            </Button>
          </div>
        )}
      </Card>

      <Section title="Datos personales">
        <Field label="Nombre" value={form.nombre} onChange={texto('nombre')} required />
        <Field label="Apellido paterno" value={form.apellido_paterno} onChange={texto('apellido_paterno')} />
        <Field label="Apellido materno" value={form.apellido_materno} onChange={texto('apellido_materno')} />
        <Field
          label="Fecha de nacimiento"
          type="date"
          value={form.fecha_nacimiento ?? ''}
          onChange={texto('fecha_nacimiento')}
        />
        <SelectField
          label="Procedencia"
          value={form.procedencia}
          onChange={(e) => setForm((f) => ({ ...f, procedencia: e.target.value as Procedencia }))}
          options={procedenciaOptions}
        />
        <Field
          label="Miembro desde"
          type="date"
          hint="Con esta fecha se calcula el tiempo en Mundo de Fe."
          value={form.miembro_desde ?? ''}
          onChange={texto('miembro_desde')}
        />
      </Section>

      <Section title="Contacto y domicilio">
        <Field label="Celular / WhatsApp" inputMode="tel" value={form.whatsapp} onChange={texto('whatsapp')} />
        <Field label="Teléfono fijo" inputMode="tel" value={form.telefono_fijo} onChange={texto('telefono_fijo')} />
        <Field label="Correo" type="email" value={form.email} onChange={texto('email')} />
        <Field label="Calle y número" value={form.calle_numero} onChange={texto('calle_numero')} />
        <Field label="Colonia" value={form.colonia} onChange={texto('colonia')} />
        <Field label="Código postal" inputMode="numeric" value={form.codigo_postal} onChange={texto('codigo_postal')} />
        <Field label="Alcaldía o municipio" value={form.alcaldia} onChange={texto('alcaldia')} />
      </Section>

      <Section title="Grupo de Conexión" description="Por ahora son datos de texto; después se ligan al módulo de Grupos.">
        <Field label="Grupo de Conexión" value={form.grupo_conexion} onChange={texto('grupo_conexion')} />
        <Field label="Líder" value={form.lider} onChange={texto('lider')} />
        <Field label="Sector" value={form.sector} onChange={texto('sector')} />
      </Section>

      <Card className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <CardTitle>Procesos de desarrollo discipular</CardTitle>
          <CardDescription>Marca los que ya cursó, con su fecha y el nombre del maestro.</CardDescription>
        </div>
        <ul className="flex flex-col gap-3">
          {form.procesos.map((p, i) => (
            <li key={p.proceso} className="grid grid-cols-1 items-center gap-3 md:grid-cols-3">
              <CheckboxField
                checked={p.completado}
                onChange={(e) => proceso(i, { completado: e.target.checked })}
                label={p.nombre}
              />
              <Field
                label={`Fecha · ${p.nombre}`}
                type="date"
                value={p.fecha ?? ''}
                onChange={(e) => proceso(i, { fecha: e.target.value || null })}
              />
              {p.pide_maestro ? (
                <Field
                  label={`Maestro · ${p.nombre}`}
                  value={p.maestro}
                  onChange={(e) => proceso(i, { maestro: e.target.value })}
                />
              ) : null}
            </li>
          ))}
        </ul>
      </Card>

      <Section title="Vida en la iglesia">
        <CheckboxField
          checked={form.sirve_en_ministerio}
          onChange={casilla('sirve_en_ministerio')}
          label="Sirve en un ministerio"
        />
        <Field label="Ministerio(s) en que sirve" value={form.ministerios} onChange={texto('ministerios')} />
        <Field label="Devocional personal" value={form.devocional_personal} onChange={texto('devocional_personal')} />
        <CheckboxField
          checked={form.oracion_familias}
          onChange={casilla('oracion_familias')}
          label="Oración de Familias en Acción (miércoles)"
        />
        <Field
          label="Detalle de la oración de familias"
          value={form.oracion_familias_detalle}
          onChange={texto('oracion_familias_detalle')}
        />
        <TextareaField label="Otros cursos" value={form.otros_cursos} onChange={texto('otros_cursos')} />
        <TextareaField label="Observaciones" value={form.observaciones} onChange={texto('observaciones')} />
      </Section>

      <Card className="flex flex-col gap-3">
        <CardTitle>Historial de movimientos</CardTitle>
        {movimientos.data?.length ? (
          <ul className="flex flex-col gap-2">
            {movimientos.data.map((m) => (
              <li key={m.id} className="flex flex-wrap gap-x-3">
                <span className="font-bold">{m.tipo_display}</span>
                <span className="text-muted-foreground">{m.fecha}</span>
                {m.iglesia_destino ? <span>→ {m.iglesia_destino}</span> : null}
                {m.motivo ? <span>{m.motivo}</span> : null}
              </li>
            ))}
          </ul>
        ) : (
          <CardDescription>Sin movimientos.</CardDescription>
        )}
      </Card>
    </form>
  )
}

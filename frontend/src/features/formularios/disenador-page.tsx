import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  CheckboxField,
  Field,
  PageHeader,
  SelectField,
  TextareaField,
} from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'
import { useFormularioExtra } from './datos-adicionales-card'
import {
  objetivoLabel,
  type CampoExtra,
  type CatalogoFormularios,
  type Entidad,
  type FilaReporte,
  type FormularioExtra,
  type Objetivo,
  type TipoCampo,
} from './types'

const TITULO: Record<Entidad, string> = { persona: 'Personas', grupo: 'Grupos de Conexión' }

export function DisenadorPage() {
  const { entidad = '' } = useParams()
  const puede = useCan('formularios.gestionar')
  const e = entidad as Entidad
  const formulario = useFormularioExtra(e)
  const catalogo = useQuery({
    queryKey: ['formularios-catalogo'],
    queryFn: () => api<CatalogoFormularios>('/api/formularios/'),
    staleTime: Infinity,
  })
  if (entidad !== 'persona' && entidad !== 'grupo') return <Alert tone="warning">No existe ese formulario.</Alert>
  if (!puede) return <Alert tone="warning">No tienes permiso para diseñar formularios.</Alert>
  if (formulario.isPending || catalogo.isPending) return <p className="text-muted-foreground">Cargando…</p>
  if (formulario.isError) return <Alert tone="destructive">{formulario.error.message}</Alert>
  if (catalogo.isError) return <Alert tone="destructive">{catalogo.error.message}</Alert>
  return <Editor key={formulario.data.version} entidad={e} formulario={formulario.data} catalogo={catalogo.data} />
}

const nuevaClave = (campos: CampoExtra[]) => {
  let n = campos.length + 1
  while (campos.some((c) => c.clave === `campo_${n}`)) n += 1
  return `campo_${n}`
}

function Editor({
  entidad,
  formulario,
  catalogo,
}: {
  entidad: Entidad
  formulario: FormularioExtra
  catalogo: CatalogoFormularios
}) {
  const queryClient = useQueryClient()
  const [campos, setCampos] = useState<CampoExtra[]>(formulario.campos)
  const existentes = new Set(formulario.campos.map((c) => c.clave))

  const guardar = useMutation({
    mutationFn: () => api<FormularioExtra>(`/api/formularios/${entidad}/`, { method: 'PUT', body: { campos } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['formulario-extra', entidad] })
      void queryClient.invalidateQueries({ queryKey: ['reporte-formulario', entidad] })
    },
  })

  const cambiar = (i: number, cambios: Partial<CampoExtra>) =>
    setCampos((lista) => lista.map((c, k) => (k === i ? { ...c, ...cambios } : c)))
  const mover = (i: number, d: -1 | 1) =>
    setCampos((lista) => {
      const j = i + d
      if (j < 0 || j >= lista.length) return lista
      const copia = [...lista]
      ;[copia[i], copia[j]] = [copia[j], copia[i]]
      return copia
    })

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={`Formulario de ${TITULO[entidad]}`}
        description={`Versión ${formulario.version}. Los campos no se borran: se desactivan, para conservar las respuestas anteriores.`}
        module="admin"
        actions={
          <Button asChild variant="outline">
            <Link to="/formularios">Volver</Link>
          </Button>
        }
      />
      {guardar.isSuccess ? <Alert tone="success">Formulario guardado.</Alert> : null}
      {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
      {campos.length === 0 ? <Alert>Aún no hay campos adicionales. Agrega el primero.</Alert> : null}

      <ul className="flex flex-col gap-3">
        {campos.map((c, i) => {
          const fijo = existentes.has(c.clave)
          return (
            <li key={c.clave}>
              <Card className="flex flex-col gap-3">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Field
                    label="Etiqueta (lo que ve quien captura)"
                    value={c.etiqueta}
                    onChange={(e) => cambiar(i, { etiqueta: e.target.value })}
                  />
                  <SelectField
                    label="Tipo de campo"
                    value={c.tipo}
                    disabled={fijo}
                    hint={fijo ? 'No se cambia en campos ya existentes.' : undefined}
                    onChange={(e) => cambiar(i, { tipo: e.target.value as TipoCampo })}
                    options={catalogo.tipos.map((t) => ({ value: t.clave, label: t.nombre }))}
                  />
                </div>
                {c.tipo === 'seleccion' ? (
                  <TextareaField
                    label="Opciones (una por línea)"
                    value={c.opciones.join('\n')}
                    onChange={(e) => cambiar(i, { opciones: e.target.value.split('\n') })}
                  />
                ) : null}
                {c.tipo === 'relacion' ? (
                  <SelectField
                    label="¿A qué apunta?"
                    value={c.objetivo}
                    disabled={fijo}
                    onChange={(e) => cambiar(i, { objetivo: e.target.value as Objetivo })}
                    options={[
                      { value: '', label: 'Elige una opción' },
                      ...catalogo.objetivos.map((o) => ({ value: o.clave, label: objetivoLabel[o.clave] })),
                    ]}
                  />
                ) : null}
                <Field
                  label="Ayuda (opcional)"
                  value={c.ayuda}
                  onChange={(e) => cambiar(i, { ayuda: e.target.value })}
                />
                <div className="flex flex-wrap items-center gap-x-6">
                  <CheckboxField
                    label="Obligatorio"
                    checked={c.requerido}
                    onChange={(e) => cambiar(i, { requerido: e.target.checked })}
                  />
                  <CheckboxField
                    label="Entra en reportes"
                    checked={c.reportable}
                    onChange={(e) => cambiar(i, { reportable: e.target.checked })}
                  />
                  <CheckboxField
                    label="Activo"
                    checked={c.activo}
                    onChange={(e) => cambiar(i, { activo: e.target.checked })}
                  />
                  <Button type="button" size="icon" variant="ghost" aria-label="Subir" onClick={() => mover(i, -1)}>
                    <ArrowUp aria-hidden className="size-5" />
                  </Button>
                  <Button type="button" size="icon" variant="ghost" aria-label="Bajar" onClick={() => mover(i, 1)}>
                    <ArrowDown aria-hidden className="size-5" />
                  </Button>
                </div>
                <CardDescription>
                  Clave interna: {c.clave} {!c.activo ? <Badge tone="warning">Desactivado</Badge> : null}
                </CardDescription>
              </Card>
            </li>
          )
        })}
      </ul>

      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={() =>
            setCampos((l) => [
              ...l,
              {
                clave: nuevaClave(l),
                etiqueta: '',
                tipo: 'texto',
                ayuda: '',
                requerido: false,
                activo: true,
                reportable: false,
                opciones: [],
                objetivo: '',
              },
            ])
          }
        >
          <Plus aria-hidden className="size-5" />
          Agregar campo
        </Button>
        <Button type="button" size="lg" onClick={() => guardar.mutate()} disabled={guardar.isPending}>
          {guardar.isPending ? 'Guardando…' : 'Guardar formulario'}
        </Button>
      </div>

      <Reporte entidad={entidad} />
    </div>
  )
}

function Reporte({ entidad }: { entidad: Entidad }) {
  const reporte = useQuery({
    queryKey: ['reporte-formulario', entidad],
    queryFn: () => api<FilaReporte[]>(`/api/formularios/${entidad}/reporte/`),
  })
  if (!reporte.data || reporte.data.length === 0) return null
  return (
    <Card className="flex flex-col gap-4">
      <CardTitle>Respuestas de los campos marcados para reportes</CardTitle>
      {reporte.data.map((f) => (
        <div key={f.clave} className="flex flex-col gap-1">
          <span className="font-bold">
            {f.etiqueta} <span className="font-normal text-muted-foreground">({f.respuestas} respuestas)</span>
          </span>
          <ul className="flex flex-col gap-1">
            {f.valores.map((v) => (
              <li key={v.valor}>
                {v.valor}: {v.total}
              </li>
            ))}
          </ul>
          {f.por_grupo ? (
            <>
              <span className="mt-1 text-sm font-semibold">Por grupo de la persona elegida</span>
              <ul className="flex flex-col gap-1">
                {f.por_grupo.map((g) => (
                  <li key={g.grupo}>
                    {g.grupo}: {g.total}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      ))}
    </Card>
  )
}

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Alert,
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
import { useFormularioPeticiones } from './peticiones-panel'
import { tipoCampoLabel, type Campo, type Formulario, type TipoCampo } from './types'

export function FormularioPage() {
  const puede = useCan('peticiones.configurar')
  const formulario = useFormularioPeticiones()
  if (!puede) return <Alert tone="warning">No tienes permiso para editar el formulario.</Alert>
  if (formulario.isPending) return <p className="text-muted-foreground">Cargando…</p>
  if (formulario.isError) return <Alert tone="destructive">{formulario.error.message}</Alert>
  return <Editor key={formulario.data.version} formulario={formulario.data} />
}

const nuevaClave = (campos: Campo[]) => {
  let n = campos.length + 1
  while (campos.some((c) => c.clave === `campo_${n}`)) n += 1
  return `campo_${n}`
}

function Editor({ formulario }: { formulario: Formulario }) {
  const queryClient = useQueryClient()
  const [campos, setCampos] = useState<Campo[]>(formulario.campos)
  const clavesExistentes = new Set(formulario.campos.map((c) => c.clave))

  const guardar = useMutation({
    mutationFn: () => api<Formulario>('/api/peticiones/formulario/', { method: 'PUT', body: { campos } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['peticiones-formulario'] }),
  })

  const cambiar = (i: number, cambios: Partial<Campo>) =>
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
        title="Formulario de peticiones"
        description={`Versión ${formulario.version}. Los campos no se borran: se desactivan, para conservar las respuestas anteriores.`}
        module="grupos"
        actions={
          <Button asChild variant="outline">
            <Link to="/peticiones">Volver</Link>
          </Button>
        }
      />
      {guardar.isSuccess ? <Alert tone="success">Formulario guardado como una versión nueva.</Alert> : null}
      {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}

      <ul className="flex flex-col gap-3">
        {campos.map((c, i) => (
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
                  disabled={clavesExistentes.has(c.clave)}
                  hint={clavesExistentes.has(c.clave) ? 'No se cambia en campos ya existentes.' : undefined}
                  onChange={(e) => cambiar(i, { tipo: e.target.value as TipoCampo })}
                  options={(Object.keys(tipoCampoLabel) as TipoCampo[]).map((t) => ({
                    value: t,
                    label: tipoCampoLabel[t],
                  }))}
                />
              </div>
              {c.tipo === 'seleccion' ? (
                <TextareaField
                  label="Opciones (una por línea)"
                  value={c.opciones.join('\n')}
                  onChange={(e) => cambiar(i, { opciones: e.target.value.split('\n') })}
                />
              ) : null}
              <div className="flex flex-wrap items-center gap-x-6">
                <CheckboxField
                  label="Obligatorio"
                  checked={c.requerido}
                  onChange={(e) => cambiar(i, { requerido: e.target.checked })}
                />
                <CheckboxField
                  label="Identifica a la persona"
                  checked={Boolean(c.identifica)}
                  onChange={(e) => cambiar(i, { identifica: e.target.checked })}
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
              <CardDescription>Clave interna: {c.clave}</CardDescription>
            </Card>
          </li>
        ))}
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
                requerido: false,
                activo: true,
                identifica: false,
                opciones: [],
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
      <CardTitle className="sr-only">Fin del formulario</CardTitle>
    </div>
  )
}

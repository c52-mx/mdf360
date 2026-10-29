import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert, Button, Card, CardDescription, CardTitle } from '@/design-system'
import { api } from '@/lib/api'
import { CamposExtra } from './campos-extra'
import type { Entidad, FormularioExtra, Respuestas } from './types'

export function useFormularioExtra(entidad: Entidad) {
  return useQuery({
    queryKey: ['formulario-extra', entidad],
    queryFn: () => api<FormularioExtra>(`/api/formularios/${entidad}/`),
    staleTime: 60_000,
  })
}

interface Props {
  entidad: Entidad
  id: number
  datos: Respuestas
  etiquetas?: Record<string, string>
  puedeEditar: boolean
  /** Consultas que deben refrescarse al guardar. */
  refrescar: unknown[]
}

/** Campos adicionales de una persona o un grupo. No aparece si el diseñador no definió ninguno. */
export function DatosAdicionalesCard({ entidad, id, datos, etiquetas, puedeEditar, refrescar }: Props) {
  const formulario = useFormularioExtra(entidad)
  if (!formulario.data || !formulario.data.campos.some((c) => c.activo)) return null
  return (
    <Formulario
      key={JSON.stringify(datos)}
      formulario={formulario.data}
      {...{ entidad, id, datos, etiquetas, puedeEditar, refrescar }}
    />
  )
}

function Formulario({
  formulario,
  entidad,
  id,
  datos,
  etiquetas,
  puedeEditar,
  refrescar,
}: Props & { formulario: FormularioExtra }) {
  const queryClient = useQueryClient()
  const [valores, setValores] = useState<Respuestas>(datos ?? {})
  const guardar = useMutation({
    mutationFn: () =>
      api(`/api/${entidad === 'persona' ? 'personas' : 'grupos'}/${id}/`, {
        method: 'PATCH',
        body: { datos_extra: valores },
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: refrescar }),
  })

  return (
    <Card className="flex flex-col gap-4">
      <CardTitle>Datos adicionales</CardTitle>
      <CardDescription>Campos que la iglesia agregó a este formulario.</CardDescription>
      <form
        className="flex max-w-xl flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault()
          guardar.mutate()
        }}
      >
        <CamposExtra
          campos={formulario.campos}
          valores={valores}
          etiquetas={etiquetas}
          onChange={setValores}
          disabled={!puedeEditar}
        />
        {guardar.isSuccess ? <Alert tone="success">Los datos adicionales se guardaron.</Alert> : null}
        {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
        {puedeEditar ? (
          <div>
            <Button type="submit" disabled={guardar.isPending}>
              Guardar datos adicionales
            </Button>
          </div>
        ) : null}
      </form>
    </Card>
  )
}

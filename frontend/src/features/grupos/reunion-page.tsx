import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  PageHeader,
  TextareaField,
} from '@/design-system'
import { api } from '@/lib/api'
import { fechaLarga, type ReunionDetalle } from './types'

export function ReunionPage() {
  const { rid = '' } = useParams()
  const reunion = useQuery({
    queryKey: ['reunion', rid],
    queryFn: () => api<ReunionDetalle>(`/api/grupos/reuniones/${rid}/`),
  })
  if (reunion.isPending) return <p className="text-muted-foreground">Cargando…</p>
  if (reunion.isError) return <Alert tone="destructive">{reunion.error.message}</Alert>
  return <Lista key={reunion.data.id} reunion={reunion.data} />
}

function Lista({ reunion }: { reunion: ReunionDetalle }) {
  const queryClient = useQueryClient()
  const [presentes, setPresentes] = useState<Record<number, boolean>>(() =>
    Object.fromEntries(reunion.personas.map((p) => [p.persona_id, p.presente])),
  )
  const [notas, setNotas] = useState(reunion.notas)
  const total = Object.values(presentes).filter(Boolean).length

  const guardar = useMutation({
    mutationFn: () =>
      api(`/api/grupos/reuniones/${reunion.id}/`, {
        method: 'PUT',
        body: {
          asistencias: Object.entries(presentes).map(([id, presente]) => ({
            persona_id: Number(id),
            presente,
          })),
          notas,
        },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['grupo', String(reunion.grupo.id)] })
      void queryClient.invalidateQueries({ queryKey: ['reunion', String(reunion.id)] })
    },
  })
  const e = reunion.estudio

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={reunion.grupo.nombre}
        description={fechaLarga(reunion.fecha)}
        module="grupos"
        actions={
          <Button asChild variant="outline">
            <Link to={`/grupos/${reunion.grupo.id}`}>Volver al grupo</Link>
          </Button>
        }
      />

      <Card className="flex flex-col gap-3">
        <CardTitle>Estudio de la semana</CardTitle>
        {e ? (
          <>
            <p className="font-bold">{e.titulo}</p>
            {e.audio ? (
              <audio controls preload="none" src={e.audio} className="w-full">
                Tu navegador no puede reproducir el audio.
              </audio>
            ) : null}
            <div className="flex flex-wrap gap-3">
              {e.pdf_adultos ? (
                <Button asChild variant="outline">
                  <a href={e.pdf_adultos} target="_blank" rel="noreferrer">
                    PDF adultos
                  </a>
                </Button>
              ) : null}
              {e.pdf_ninos ? (
                <Button asChild variant="outline">
                  <a href={e.pdf_ninos} target="_blank" rel="noreferrer">
                    PDF niños
                  </a>
                </Button>
              ) : null}
            </div>
          </>
        ) : (
          <CardDescription>Todavía no se ha publicado el estudio de esta semana.</CardDescription>
        )}
      </Card>

      <Card className="flex flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <CardTitle>Pasar lista</CardTitle>
          <span className="font-bold text-success">
            {total} de {reunion.personas.length} presentes
          </span>
        </div>
        {!reunion.puede_modificar ? (
          <Alert tone="warning">Solo puedes consultar esta lista.</Alert>
        ) : null}
        <ul className="flex flex-col gap-2">
          {reunion.personas.map((p) => (
            <li key={p.persona_id} className="flex items-center justify-between gap-3">
              <span>
                <span className="font-bold">{p.nombre}</span>{' '}
                {p.invitado ? <Badge tone="warning">Invitado</Badge> : null}
              </span>
              <Button
                type="button"
                variant={presentes[p.persona_id] ? 'success' : 'outline'}
                disabled={!reunion.puede_modificar}
                aria-pressed={presentes[p.persona_id]}
                onClick={() => setPresentes((m) => ({ ...m, [p.persona_id]: !m[p.persona_id] }))}
                className="min-w-28"
              >
                {presentes[p.persona_id] ? 'Presente' : 'Ausente'}
              </Button>
            </li>
          ))}
        </ul>
        <TextareaField
          label="Notas de la reunión"
          value={notas}
          disabled={!reunion.puede_modificar}
          onChange={(ev) => setNotas(ev.target.value)}
        />
        {guardar.isSuccess ? <Alert tone="success">Lista guardada.</Alert> : null}
        {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
        {reunion.puede_modificar ? (
          <Button size="lg" onClick={() => guardar.mutate()} disabled={guardar.isPending}>
            {guardar.isPending ? 'Guardando…' : 'Guardar lista'}
          </Button>
        ) : null}
      </Card>
    </div>
  )
}

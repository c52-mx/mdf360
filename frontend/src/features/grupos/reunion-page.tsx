import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Alert, Button, Card, CardDescription, CardTitle, PageHeader } from '@/design-system'
import { useAuth } from '@/features/auth/use-auth'
import { api } from '@/lib/api'
import { esErrorDeRed, pendientes } from '@/lib/outbox'
import { ListaAsistencia, type ResultadoGuardado } from './lista-asistencia'
import { PeticionesPanel } from '@/features/peticiones/peticiones-panel'
import { OfrendasReunion } from './ofrendas'
import { fechaLarga, type ReunionDetalle } from './types'

export function ReunionPage() {
  const { rid = '' } = useParams()
  const reunion = useQuery({
    queryKey: ['reunion', rid],
    queryFn: () => api<ReunionDetalle>(`/api/grupos/reuniones/${rid}/`),
  })
  if (reunion.isPending) return <p className="text-muted-foreground">Cargando…</p>
  if (reunion.isError) return <Alert tone="destructive">{reunion.error.message}</Alert>
  return <Reunion key={reunion.data.id} reunion={reunion.data} />
}

function Reunion({ reunion }: { reunion: ReunionDetalle }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const e = reunion.estudio

  const guardar = async (
    asistencias: { persona_id: number; presente: boolean }[],
    notas: string,
  ): Promise<ResultadoGuardado> => {
    try {
      await api(`/api/grupos/reuniones/${reunion.id}/`, { method: 'PUT', body: { asistencias, notas } })
      void queryClient.invalidateQueries({ queryKey: ['grupo', String(reunion.grupo.id)] })
      void queryClient.invalidateQueries({ queryKey: ['reunion', String(reunion.id)] })
      return 'enviado'
    } catch (error) {
      if (!esErrorDeRed(error) || !user) throw error
      pendientes.agregar({
        usuarioId: user.id,
        grupoId: reunion.grupo.id,
        grupoNombre: reunion.grupo.nombre,
        fecha: reunion.fecha,
        reunionId: reunion.id,
        asistencias,
        notas,
        capturadoEn: new Date().toISOString(),
      })
      return 'en-cola'
    }
  }

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

      <ListaAsistencia
        personas={reunion.personas}
        notasIniciales={reunion.notas}
        puedeModificar={reunion.puede_modificar}
        onGuardar={guardar}
      />

      <PeticionesPanel
        origenTipo="grupo"
        origenId={reunion.grupo.id}
        referenciaId={reunion.id}
        puedeRegistrar={reunion.puede_modificar}
      />

      <OfrendasReunion reunionId={reunion.id} />
    </div>
  )
}

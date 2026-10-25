import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Alert, Button, PageHeader } from '@/design-system'
import { useAuth } from '@/features/auth/use-auth'
import { api } from '@/lib/api'
import { pendientes } from '@/lib/outbox'
import { ListaAsistencia, type PersonaLista } from './lista-asistencia'
import { fechaLarga, type GrupoDetalle } from './types'

/** Fecha local de hoy (AAAA-MM-DD), no la UTC: la reunión es del día en que está el teléfono. */
function hoyLocal() {
  const d = new Date()
  const mes = String(d.getMonth() + 1).padStart(2, '0')
  const dia = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mes}-${dia}`
}

/**
 * Pase de lista de hoy cuando no hay conexión. Usa la lista de integrantes que el teléfono ya
 * conoce (se guardó la última vez que se abrió el grupo con señal) y deja la captura en cola.
 */
export function ListaSinConexionPage() {
  const { id = '' } = useParams()
  const { user } = useAuth()
  const grupo = useQuery({
    queryKey: ['grupo', id],
    queryFn: () => api<GrupoDetalle>(`/api/grupos/${id}/`),
    retry: false,
  })

  if (grupo.isPending) return <p className="text-muted-foreground">Cargando…</p>
  if (grupo.isError || !grupo.data) {
    return (
      <Alert tone="destructive">
        Este grupo todavía no está guardado en tu teléfono. Ábrelo una vez con conexión para poder
        pasar lista sin señal.
      </Alert>
    )
  }
  const g = grupo.data
  const vistos = new Set<number>()
  const personas: PersonaLista[] = g.miembros
    .filter((m) => (vistos.has(m.persona_id) ? false : vistos.add(m.persona_id)))
    .map((m) => ({ persona_id: m.persona_id, nombre: m.nombre, invitado: m.invitado, presente: false }))
  const fecha = hoyLocal()

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={g.nombre}
        description={fechaLarga(fecha)}
        module="grupos"
        actions={
          <Button asChild variant="outline">
            <Link to={`/grupos/${g.id}`}>Volver al grupo</Link>
          </Button>
        }
      />
      <Alert tone="warning">
        Sin conexión: la lista se guarda en tu teléfono y se envía sola cuando haya señal.
      </Alert>
      <ListaAsistencia
        personas={personas}
        notasIniciales=""
        puedeModificar
        onGuardar={async (asistencias, notas) => {
          if (!user) throw new Error('Inicia sesión para guardar la lista.')
          pendientes.agregar({
            usuarioId: user.id,
            grupoId: g.id,
            grupoNombre: g.nombre,
            fecha,
            asistencias,
            notas,
            capturadoEn: new Date().toISOString(),
          })
          return 'en-cola'
        }}
      />
    </div>
  )
}

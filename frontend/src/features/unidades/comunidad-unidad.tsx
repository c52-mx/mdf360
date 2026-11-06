import { Heart, MessageCircle } from 'lucide-react'
import { Avatar, Badge, Button, Card, CardDescription, CardTitle } from '@/design-system'
import { TableroPanel } from '@/features/tablero/tablero-panel'
import type { UnidadDetalle } from './types'

/**
 * MAQUETA de la vista tipo red social para quien sirve en un ministerio sin encargarse de él.
 * El equipo y el muro son reales; las reacciones, los comentarios y la agenda aún no existen y
 * se muestran de ejemplo, marcados como maqueta, para validar el diseño antes de construirlo.
 */
export function ComunidadUnidad({ unidad }: { unidad: UnidadDetalle }) {
  const equipo = unidad.miembros
  return (
    <div className="flex flex-col gap-6">
      <Card className="flex flex-col gap-2 bg-primary-soft">
        <Badge tone="primary">Tu ministerio</Badge>
        <h2 className="font-display text-2xl font-bold">{unidad.nombre}</h2>
        <CardDescription>{unidad.descripcion || 'Sirviendo juntos.'}</CardDescription>
        <CardDescription>
          {equipo.length} {equipo.length === 1 ? 'persona sirve' : 'personas sirven'} aquí
          {unidad.encargados.length > 0 ? ` · Encargado: ${unidad.encargados.join(', ')}` : ''}
        </CardDescription>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <TableroPanel origenTipo="unidad" origenId={unidad.id} puedePublicar={unidad.puede_gestionar} />

          <Card className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle>Así se vería una publicación</CardTitle>
              <Badge tone="warning">Maqueta</Badge>
            </div>
            <div className="flex items-start gap-3">
              <Avatar name="Ana Ejemplo" />
              <div className="flex flex-col gap-1">
                <span className="font-bold">Ana Ejemplo</span>
                <p>¡Gracias a todos por el servicio del domingo! Faltan dos manos para el próximo turno.</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant="outline" disabled>
                <Heart aria-hidden className="size-4" />
                Me da gusto
              </Button>
              <Button size="sm" variant="outline" disabled>
                <MessageCircle aria-hidden className="size-4" />
                Comentar
              </Button>
            </div>
            <CardDescription>
              Reacciones y comentarios aún no funcionan: es solo para que veas la idea.
            </CardDescription>
          </Card>
        </div>

        <div className="flex flex-col gap-6">
          <Card className="flex flex-col gap-3">
            <CardTitle>Mi equipo</CardTitle>
            <ul className="flex flex-col gap-3">
              {equipo.map((m) => (
                <li key={m.id} className="flex items-center gap-3">
                  <Avatar name={m.nombre} />
                  <span className="flex min-w-0 flex-col">
                    <span className="font-semibold">{m.nombre}</span>
                    <span className="text-sm text-muted-foreground">{m.rol_display}</span>
                  </span>
                </li>
              ))}
            </ul>
          </Card>
          <Card className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle>Próximos turnos</CardTitle>
              <Badge tone="warning">Maqueta</Badge>
            </div>
            <CardDescription>
              Aquí aparecerían tus turnos y jornadas. La agenda y el calendario siguen en definición.
            </CardDescription>
          </Card>
        </div>
      </div>
    </div>
  )
}

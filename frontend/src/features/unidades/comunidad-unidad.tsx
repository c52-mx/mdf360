import { Badge, Card, CardDescription } from '@/design-system'
import { MuroFeed } from '@/features/muro/muro-feed'
import type { UnidadDetalle } from './types'

/**
 * Vista de quien sirve en un ministerio sin encargarse de él: su servicio y el muro del
 * ministerio. Solo contenido: no se muestran perfiles, fotos ni datos de las demás personas.
 */
export function ComunidadUnidad({ unidad }: { unidad: UnidadDetalle }) {
  const roles = unidad.mis_roles.length > 0 ? unidad.mis_roles.join(', ') : null
  return (
    <div className="flex flex-col gap-6">
      <Card className="flex flex-col gap-2 bg-primary-soft">
        <Badge tone="primary">Mi servicio</Badge>
        <h2 className="font-display text-2xl font-bold">{unidad.nombre}</h2>
        <CardDescription>{unidad.descripcion || 'Sirviendo juntos.'}</CardDescription>
        {roles ? <CardDescription>Sirves aquí como {roles}.</CardDescription> : null}
        {unidad.encargados.length > 0 ? (
          <CardDescription>Encargado: {unidad.encargados.join(', ')}</CardDescription>
        ) : null}
      </Card>
      <MuroFeed audiencia={{ tipo: 'unidad', id: unidad.id }} />
    </div>
  )
}

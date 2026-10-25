import { MapPin } from 'lucide-react'
import { Badge } from '@/design-system'
import type { Origen } from './types'

/** Muestra siempre de dónde viene una petición. Va en toda vista donde aparece una petición. */
export function OrigenBadge({ origen }: { origen: Origen }) {
  return (
    <Badge tone="primary" title={origen.tipo_display}>
      <MapPin aria-hidden className="size-4" />
      {origen.etiqueta}
    </Badge>
  )
}

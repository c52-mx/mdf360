import type { ReactNode } from 'react'
import { TriangleAlert } from 'lucide-react'

interface DangerZoneProps {
  /** Acciones difíciles de deshacer (cada una con su ConfirmButton). */
  children: ReactNode
  title?: string
}

/** Al final de una pantalla: aparta lo que suspende, da de baja o borra, para no tocarlo sin querer. */
export function DangerZone({ children, title = 'Zona de riesgo' }: DangerZoneProps) {
  return (
    <section
      aria-label={title}
      className="flex flex-col gap-4 rounded-card border-2 border-destructive bg-destructive-soft p-4"
    >
      <h2 className="flex items-center gap-2 text-xl font-bold text-destructive">
        <TriangleAlert aria-hidden className="size-6" />
        {title}
      </h2>
      <div className="flex flex-col gap-4">{children}</div>
    </section>
  )
}

interface DangerActionProps {
  title: string
  description: string
  children: ReactNode
}

/** Una acción de la zona de riesgo: qué hace, y el botón que la ejecuta con confirmación. */
export function DangerAction({ title, description, children }: DangerActionProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-1">
        <p className="font-bold">{title}</p>
        <p className="text-muted-foreground">{description}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}

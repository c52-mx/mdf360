import type { ReactNode } from 'react'
import { Card, CardDescription, CardTitle } from './card'

interface SectionProps {
  title: string
  description?: string
  children: ReactNode
}

/** Bloque de un formulario largo: título, ayuda opcional y contenido en cuadrícula adaptable. */
export function Section({ title, description, children }: SectionProps) {
  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{children}</div>
    </Card>
  )
}

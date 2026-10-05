import type { ReactNode } from 'react'
import { moduleBg, type ModuleKey } from './module'
import { cn } from '@/lib/cn'

interface PageHeaderProps {
  title: string
  description?: string
  module?: ModuleKey
  actions?: ReactNode
}

/** Encabezado estándar de cada pantalla: título, descripción, color del módulo y acciones. */
export function PageHeader({ title, description, module, actions }: PageHeaderProps) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        {module ? <span aria-hidden className={cn('h-9 w-3 rounded', moduleBg[module])} /> : null}
        <div>
          <h1 className="text-2xl leading-tight">{title}</h1>
          {description ? <p className="text-muted-foreground">{description}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
    </header>
  )
}

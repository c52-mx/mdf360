import { useState, type ReactNode } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/cn'

interface CollapsibleProps {
  title: string
  /** Dato breve junto al título, p. ej. «12 peticiones». */
  summary?: string
  defaultOpen?: boolean
  /** Avisa al abrir o cerrar; sirve para pedir los datos solo cuando se consultan. */
  onToggle?: (open: boolean) => void
  children: ReactNode
}

/**
 * Sección que arranca cerrada. El contenido no se dibuja hasta abrirla, así lo reservado
 * (peticiones, historial) no se carga ni se muestra si nadie lo consulta.
 */
export function Collapsible({ title, summary, defaultOpen = false, onToggle, children }: CollapsibleProps) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <section className="rounded-card border border-border bg-card">
      <h2 className="text-xl">
        <button
          type="button"
          aria-expanded={open}
          onClick={() => {
            setOpen(!open)
            onToggle?.(!open)
          }}
          className="flex min-h-14 w-full items-center justify-between gap-3 rounded-card px-4 py-3 text-left"
        >
          <span className="flex flex-col">
            <span className="font-bold">{title}</span>
            {summary ? <span className="text-base font-normal text-muted-foreground">{summary}</span> : null}
          </span>
          <ChevronDown aria-hidden className={cn('size-6 shrink-0 transition-transform', open && 'rotate-180')} />
        </button>
      </h2>
      {open ? <div className="border-t border-border p-4">{children}</div> : null}
    </section>
  )
}

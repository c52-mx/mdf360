import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

export interface Pestana {
  id: string
  titulo: string
  contenido: ReactNode
}

interface TabsProps {
  /** Nombre de la lista de pestañas, para lectores de pantalla. */
  titulo: string
  pestanas: Pestana[]
  /** Pestaña con la que se abre; por defecto la primera. */
  inicial?: string
}

/**
 * Pestañas para formularios largos: se puede ir a cualquiera en cualquier momento, ninguna es
 * obligatoria. Teclado: flechas, Inicio y Fin. Solo se dibuja la pestaña activa; lo que la
 * persona escribe debe vivir en el estado de la pantalla, no en los campos.
 */
export function Tabs({ titulo, pestanas, inicial }: TabsProps) {
  const base = useId()
  const [activa, setActiva] = useState(inicial ?? pestanas[0]?.id)
  const botones = useRef<Record<string, HTMLButtonElement | null>>({})

  function mover(e: KeyboardEvent, indice: number) {
    const ultimo = pestanas.length - 1
    const destino =
      e.key === 'ArrowRight' ? (indice + 1) % pestanas.length
      : e.key === 'ArrowLeft' ? (indice - 1 + pestanas.length) % pestanas.length
      : e.key === 'Home' ? 0
      : e.key === 'End' ? ultimo
      : null
    if (destino === null) return
    e.preventDefault()
    const siguiente = pestanas[destino]
    setActiva(siguiente.id)
    botones.current[siguiente.id]?.focus()
  }

  const actual = pestanas.find((p) => p.id === activa) ?? pestanas[0]
  if (!actual) return null

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" aria-label={titulo} className="flex gap-1 overflow-x-auto border-b-2 border-border">
        {pestanas.map((p, i) => {
          const seleccionada = p.id === actual.id
          return (
            <button
              key={p.id}
              ref={(el) => {
                botones.current[p.id] = el
              }}
              type="button"
              role="tab"
              id={`${base}-${p.id}`}
              aria-selected={seleccionada}
              aria-controls={`${base}-panel`}
              tabIndex={seleccionada ? 0 : -1}
              onClick={() => setActiva(p.id)}
              onKeyDown={(e) => mover(e, i)}
              className={cn(
                '-mb-0.5 min-h-12 shrink-0 rounded-t-control border-b-4 px-4 font-bold',
                seleccionada
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )}
            >
              {p.titulo}
            </button>
          )
        })}
      </div>
      <div role="tabpanel" id={`${base}-panel`} aria-labelledby={`${base}-${actual.id}`} className="flex flex-col gap-4">
        {actual.contenido}
      </div>
    </div>
  )
}

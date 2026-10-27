import { Check } from 'lucide-react'
import { useState } from 'react'
import { aplicarTema, temaGuardado, TEMAS, type TemaClave } from '@/lib/tema'
import { cn } from '@/lib/cn'

/** Selector de la paleta de color de la aplicación. Cada muestra se pinta con su propia paleta. */
export function ThemePicker() {
  const [actual, setActual] = useState<TemaClave>(temaGuardado)
  const elegir = (clave: TemaClave) => {
    aplicarTema(clave)
    setActual(clave)
  }
  return (
    <div role="radiogroup" aria-label="Color de la aplicación" className="flex flex-wrap gap-3">
      {TEMAS.map((t) => {
        const activo = t.clave === actual
        return (
          <button
            key={t.clave}
            type="button"
            role="radio"
            aria-checked={activo}
            data-tema={t.clave === 'morado' ? undefined : t.clave}
            onClick={() => elegir(t.clave)}
            className={cn(
              'presionable flex h-14 items-center gap-3 rounded-control border-2 bg-card px-3 font-semibold',
              activo ? 'border-primary' : 'border-border',
            )}
          >
            <span className="flex size-8 items-center justify-center rounded-full bg-primary text-primary-foreground">
              {activo ? <Check aria-hidden className="size-5" /> : null}
            </span>
            {t.nombre}
          </button>
        )
      })}
    </div>
  )
}

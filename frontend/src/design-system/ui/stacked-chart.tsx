import { cn } from '@/lib/cn'

export interface ColumnaApilada {
  etiqueta: string
  /** Conteos por serie, en el mismo orden que `series`. */
  valores: number[]
}

export interface SerieApilada {
  nombre: string
  tone: 'warning' | 'destructive'
}

interface StackedChartProps {
  titulo: string
  series: SerieApilada[]
  columnas: ColumnaApilada[]
  className?: string
}

const colorDe: Record<SerieApilada['tone'], string> = {
  warning: 'bg-warning',
  destructive: 'bg-destructive',
}

/** Columnas apiladas de conteos (ej. errores y avisos por día). Cada columna escribe su total. */
export function StackedChart({ titulo, series, columnas, className }: StackedChartProps) {
  const maximo = Math.max(1, ...columnas.map((c) => c.valores.reduce((a, b) => a + b, 0)))
  return (
    <figure className={cn('flex flex-col gap-2', className)}>
      <figcaption className="font-bold">{titulo}</figcaption>
      <ul className="flex flex-wrap gap-4 text-sm" aria-label="Leyenda">
        {series.map((s) => (
          <li key={s.nombre} className="flex items-center gap-2">
            <span aria-hidden className={cn('size-3 rounded-full', colorDe[s.tone])} />
            {s.nombre}
          </li>
        ))}
      </ul>
      <ul className="grid auto-cols-fr grid-flow-col items-end gap-1" aria-label={titulo}>
        {columnas.map((c) => {
          const total = c.valores.reduce((a, b) => a + b, 0)
          return (
            <li
              key={c.etiqueta}
              className="flex flex-col items-center gap-1 text-xs"
              title={series.map((s, i) => `${s.nombre}: ${c.valores[i] ?? 0}`).join(' · ')}
            >
              <span className="font-bold">{total}</span>
              <div className="flex h-28 w-full flex-col-reverse overflow-hidden rounded-control bg-muted">
                {series.map((s, i) => (
                  <div
                    key={s.nombre}
                    className={colorDe[s.tone]}
                    // La altura depende del dato; es el único estilo en línea y vive en el sistema de diseño.
                    style={{ height: `${((c.valores[i] ?? 0) / maximo) * 100}%` }}
                  />
                ))}
              </div>
              <span className="text-muted-foreground">{c.etiqueta}</span>
            </li>
          )
        })}
      </ul>
    </figure>
  )
}

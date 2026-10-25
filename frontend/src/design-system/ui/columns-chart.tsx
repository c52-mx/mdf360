import { cn } from '@/lib/cn'

export interface Columna {
  etiqueta: string
  /** 0 a 100, o null si no hubo datos ese periodo. */
  valor: number | null
  detalle?: string
}

interface ColumnsChartProps {
  titulo: string
  columnas: Columna[]
  className?: string
}

/** Gráfica de columnas sencilla (porcentajes). Cada columna lleva su valor escrito. */
export function ColumnsChart({ titulo, columnas, className }: ColumnsChartProps) {
  return (
    <figure className={cn('flex flex-col gap-2', className)}>
      <figcaption className="font-bold">{titulo}</figcaption>
      <ul className="grid auto-cols-fr grid-flow-col items-end gap-2" aria-label={titulo}>
        {columnas.map((c) => (
          <li
            key={c.etiqueta}
            className="flex flex-col items-center gap-1 text-sm"
            title={c.detalle}
          >
            <span className="font-bold">{c.valor === null ? '–' : `${c.valor}%`}</span>
            <div className="flex h-32 w-full items-end rounded-control bg-muted">
              <div
                className="w-full rounded-control bg-module-grupos"
                style={{ height: `${c.valor ?? 0}%` }}
              />
            </div>
            <span className="text-muted-foreground">{c.etiqueta}</span>
          </li>
        ))}
      </ul>
    </figure>
  )
}

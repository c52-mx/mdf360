import { cn } from '@/lib/cn'

export interface PuntoLinea {
  etiqueta: string
  valor: number | null
}

export interface SerieLinea {
  nombre: string
  puntos: PuntoLinea[]
}

interface LineChartProps {
  titulo: string
  series: SerieLinea[]
  /** Texto después del valor, p. ej. «%». */
  unidad?: string
  /** Formato del valor en la tabla de apoyo. */
  formato?: (valor: number) => string
  className?: string
}

// Una clase de color por serie; el trazo se distingue también por el estilo de línea (no solo color)
const ESTILOS = [
  { trazo: 'text-module-grupos', guion: undefined },
  { trazo: 'text-accent', guion: '6 4' },
  { trazo: 'text-module-cursos', guion: '2 4' },
  { trazo: 'text-primary', guion: '10 4 2 4' },
] as const

const ANCHO = 320
const ALTO = 140
const MARGEN = { izq: 8, der: 8, arr: 10, aba: 10 }

/**
 * Gráfica de líneas para valores que cambian en el tiempo. Las categorías se comparan mejor en
 * barras (ColumnsChart). Incluye una tabla con los valores para quien no ve la gráfica.
 */
export function LineChart({ titulo, series, unidad = '', formato, className }: LineChartProps) {
  const etiquetas = series[0]?.puntos.map((p) => p.etiqueta) ?? []
  const valores = series.flatMap((s) => s.puntos.map((p) => p.valor).filter((v): v is number => v !== null))
  const max = Math.max(1, ...valores)
  const x = (i: number) =>
    MARGEN.izq +
    (etiquetas.length <= 1 ? (ANCHO - MARGEN.izq - MARGEN.der) / 2 : (i * (ANCHO - MARGEN.izq - MARGEN.der)) / (etiquetas.length - 1))
  const y = (v: number) => MARGEN.arr + (1 - v / max) * (ALTO - MARGEN.arr - MARGEN.aba)
  const mostrar = (v: number | null) => (v === null ? '–' : formato ? formato(v) : `${v}${unidad}`)

  return (
    <figure className={cn('flex flex-col gap-2', className)}>
      <figcaption className="font-bold">{titulo}</figcaption>
      {valores.length === 0 ? (
        <p className="text-muted-foreground">Aún no hay datos para mostrar.</p>
      ) : (
        <>
          <svg viewBox={`0 0 ${ANCHO} ${ALTO}`} role="img" aria-label={titulo} className="w-full">
            {[0, 0.5, 1].map((t) => (
              <line
                key={t}
                x1={MARGEN.izq}
                x2={ANCHO - MARGEN.der}
                y1={y(max * t)}
                y2={y(max * t)}
                className="stroke-border"
                strokeWidth={1}
              />
            ))}
            {series.map((s, si) => {
              const estilo = ESTILOS[si % ESTILOS.length]
              // Un hueco (null) corta la línea en vez de unir puntos que no son consecutivos
              const tramos: string[] = []
              let actual = ''
              s.puntos.forEach((p, i) => {
                if (p.valor === null) {
                  if (actual) tramos.push(actual)
                  actual = ''
                } else actual += `${actual ? 'L' : 'M'}${x(i)},${y(p.valor)}`
              })
              if (actual) tramos.push(actual)
              return (
                <g key={s.nombre} className={estilo.trazo}>
                  {tramos.map((d) => (
                    <path
                      key={d}
                      d={d}
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2.5}
                      strokeDasharray={estilo.guion}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  ))}
                  {s.puntos.map((p, i) =>
                    p.valor === null ? null : (
                      <circle key={p.etiqueta} cx={x(i)} cy={y(p.valor)} r={3.5} fill="currentColor">
                        <title>{`${s.nombre} · ${p.etiqueta}: ${mostrar(p.valor)}`}</title>
                      </circle>
                    ),
                  )}
                </g>
              )
            })}
          </svg>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-label="Series">
            {series.map((s, si) => (
              <li key={s.nombre} className="flex items-center gap-2">
                <svg viewBox="0 0 24 6" className={cn('w-6', ESTILOS[si % ESTILOS.length].trazo)} aria-hidden>
                  <line
                    x1="0"
                    x2="24"
                    y1="3"
                    y2="3"
                    stroke="currentColor"
                    strokeWidth={3}
                    strokeDasharray={ESTILOS[si % ESTILOS.length].guion}
                  />
                </svg>
                {s.nombre}
              </li>
            ))}
          </ul>
          <table className="sr-only">
            <caption>{titulo}</caption>
            <thead>
              <tr>
                <th scope="col">Periodo</th>
                {series.map((s) => (
                  <th key={s.nombre} scope="col">
                    {s.nombre}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {etiquetas.map((e, i) => (
                <tr key={e}>
                  <th scope="row">{e}</th>
                  {series.map((s) => (
                    <td key={s.nombre}>{mostrar(s.puntos[i]?.valor ?? null)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex justify-between text-sm text-muted-foreground" aria-hidden>
            <span>{etiquetas[0]}</span>
            {etiquetas.length > 1 ? <span>{etiquetas[etiquetas.length - 1]}</span> : null}
          </div>
        </>
      )}
    </figure>
  )
}

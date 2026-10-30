import { useMemo, useState, type ReactNode } from 'react'
import { ArrowDown, ArrowUp, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/cn'
import { TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from './table'

export interface DataColumn<T> {
  clave: string
  titulo: string
  celda: (fila: T) => ReactNode
  /** Valor por el que se ordena; si falta, la columna no se puede ordenar. */
  orden?: (fila: T) => string | number | null
  /** Alinea a la derecha (cantidades). */
  numerica?: boolean
}

interface DataTableProps<T> {
  titulo: string
  columnas: DataColumn<T>[]
  filas: T[]
  clave: (fila: T) => string | number
  ordenInicial?: { clave: string; descendente?: boolean }
  /** Texto cuando no hay filas. */
  vacio?: string
  /** Fila de totales al pie (finanzas): se queda visible al desplazar. */
  pie?: ReactNode
}

const colator = new Intl.Collator('es', { sensitivity: 'base', numeric: true })

function comparar(a: string | number | null, b: string | number | null) {
  if (a === null || b === null) return a === b ? 0 : a === null ? 1 : -1 // vacíos al final
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return colator.compare(String(a), String(b))
}

/**
 * Tabla para listas que crecen: encabezado fijo, desplazamiento propio y orden por columna.
 * Sustituye a las listas de tarjetas que se alargan hacia abajo.
 */
export function DataTable<T>({
  titulo,
  columnas,
  filas,
  clave,
  ordenInicial,
  vacio = 'No hay registros.',
  pie,
}: DataTableProps<T>) {
  const [orden, setOrden] = useState(ordenInicial ?? null)

  const visibles = useMemo(() => {
    const columna = columnas.find((c) => c.clave === orden?.clave)
    if (!columna?.orden || !orden) return filas
    const valor = columna.orden
    const copia = [...filas].sort((x, y) => comparar(valor(x), valor(y)))
    return orden.descendente ? copia.reverse() : copia
  }, [columnas, filas, orden])

  function alternar(c: DataColumn<T>) {
    setOrden((actual) =>
      actual?.clave === c.clave
        ? actual.descendente
          ? null
          : { clave: c.clave, descendente: true }
        : { clave: c.clave },
    )
  }

  return (
    <div
      className="max-h-[32rem] overflow-auto rounded-card border border-border bg-card"
      role="region"
      aria-label={titulo}
      tabIndex={0}
    >
      <table className="w-full border-collapse text-left">
        <caption className="sr-only">{titulo}</caption>
        <TableHead className="sticky top-0 z-10 bg-muted text-sm text-muted-foreground">
          <tr>
            {columnas.map((c) => {
              const activa = orden?.clave === c.clave
              const Icono = !activa ? ChevronsUpDown : orden?.descendente ? ArrowDown : ArrowUp
              return (
                <TableHeaderCell
                  key={c.clave}
                  className={cn(c.numerica && 'text-right')}
                  aria-sort={
                    activa ? (orden?.descendente ? 'descending' : 'ascending') : c.orden ? 'none' : undefined
                  }
                >
                  {c.orden ? (
                    <button
                      type="button"
                      onClick={() => alternar(c)}
                      className={cn(
                        'inline-flex items-center gap-1 rounded-control font-bold',
                        c.numerica && 'flex-row-reverse',
                      )}
                    >
                      {c.titulo}
                      <Icono aria-hidden className={cn('size-4', !activa && 'opacity-50')} />
                    </button>
                  ) : (
                    c.titulo
                  )}
                </TableHeaderCell>
              )
            })}
          </tr>
        </TableHead>
        <TableBody>
          {visibles.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columnas.length} className="text-center text-muted-foreground">
                {vacio}
              </TableCell>
            </TableRow>
          ) : (
            visibles.map((fila) => (
              <TableRow key={clave(fila)}>
                {columnas.map((c) => (
                  <TableCell key={c.clave} className={cn(c.numerica && 'text-right tabular-nums')}>
                    {c.celda(fila)}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
        {pie ? (
          <tfoot className="sticky bottom-0 bg-muted font-bold">{pie}</tfoot>
        ) : null}
      </table>
    </div>
  )
}

import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DataTable, type DataColumn } from './data-table'

interface Fila {
  id: number
  origen: string
  monto: number | null
}
const filas: Fila[] = [
  { id: 1, origen: 'Norte', monto: 300 },
  { id: 2, origen: 'álamo', monto: 1200 },
  { id: 3, origen: 'Sur', monto: null },
]
const columnas: DataColumn<Fila>[] = [
  { clave: 'origen', titulo: 'Origen', celda: (f) => f.origen, orden: (f) => f.origen },
  { clave: 'monto', titulo: 'Monto', numerica: true, celda: (f) => f.monto ?? '–', orden: (f) => f.monto },
  { clave: 'nota', titulo: 'Nota', celda: () => 'x' },
]

const orden = () =>
  within(screen.getByRole('table'))
    .getAllByRole('row')
    .slice(1)
    .map((r) => r.firstChild?.textContent)

function montar() {
  render(<DataTable titulo="Ofrendas" columnas={columnas} filas={filas} clave={(f) => f.id} />)
}

describe('DataTable', () => {
  it('muestra las filas en el orden recibido', () => {
    montar()
    expect(orden()).toEqual(['Norte', 'álamo', 'Sur'])
  })

  it('ordena por texto ignorando acentos y alterna ascendente, descendente y sin orden', () => {
    montar()
    const boton = screen.getByRole('button', { name: 'Origen' })
    fireEvent.click(boton)
    expect(orden()).toEqual(['álamo', 'Norte', 'Sur'])
    expect(screen.getByRole('columnheader', { name: 'Origen' })).toHaveAttribute('aria-sort', 'ascending')
    fireEvent.click(boton)
    expect(orden()).toEqual(['Sur', 'Norte', 'álamo'])
    fireEvent.click(boton)
    expect(orden()).toEqual(['Norte', 'álamo', 'Sur'])
  })

  it('ordena números y deja los vacíos al final', () => {
    montar()
    fireEvent.click(screen.getByRole('button', { name: 'Monto' }))
    expect(orden()).toEqual(['Norte', 'álamo', 'Sur'])
    fireEvent.click(screen.getByRole('button', { name: 'Monto' }))
    expect(orden()[0]).toBe('Sur') // descendente: invierte, los vacíos pasan al inicio
  })

  it('una columna sin orden no es un botón', () => {
    montar()
    expect(screen.queryByRole('button', { name: 'Nota' })).not.toBeInTheDocument()
  })

  it('avisa cuando no hay filas y muestra el pie de totales', () => {
    render(
      <DataTable
        titulo="Vacía"
        columnas={columnas}
        filas={[]}
        clave={(f) => f.id}
        vacio="Sin ofrendas."
        pie={
          <tr>
            <td>Total</td>
          </tr>
        }
      />,
    )
    expect(screen.getByText('Sin ofrendas.')).toBeInTheDocument()
    expect(screen.getByText('Total')).toBeInTheDocument()
  })
})

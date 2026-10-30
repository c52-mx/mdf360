import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { ComboField } from './combo-field'

const personas = [
  { value: '1', label: 'Ángela Pérez', detalle: '55 1234 5678' },
  { value: '2', label: 'Luis Gómez', detalle: '55 9999 0000' },
  { value: '3', label: 'Lucía Núñez', detalle: '33 4444 1111' },
]

function Probar({ inicial = '' }: { inicial?: string }) {
  const [v, setV] = useState(inicial)
  return (
    <>
      <ComboField label="Persona" options={personas} value={v} onChange={setV} />
      <output aria-label="elegido">{v}</output>
    </>
  )
}

const caja = () => screen.getByRole('combobox', { name: 'Persona' })
const opciones = () => screen.queryAllByRole('option').map((o) => o.textContent)

describe('ComboField', () => {
  it('filtra por nombre sin importar acentos ni mayúsculas', () => {
    render(<Probar />)
    fireEvent.change(caja(), { target: { value: 'angela' } })
    expect(opciones()).toEqual(['Ángela Pérez55 1234 5678'])
  })

  it('filtra por número aunque se escriba sin espacios', () => {
    render(<Probar />)
    fireEvent.change(caja(), { target: { value: '5599' } })
    expect(opciones()).toEqual(['Luis Gómez55 9999 0000'])
  })

  it('avisa cuando nadie coincide', () => {
    render(<Probar />)
    fireEvent.change(caja(), { target: { value: 'zzz' } })
    expect(screen.getByText('Nadie coincide con la búsqueda.')).toBeInTheDocument()
  })

  it('elige con el clic y muestra el nombre', () => {
    render(<Probar />)
    fireEvent.change(caja(), { target: { value: 'lu' } })
    fireEvent.click(screen.getByRole('option', { name: /Lucía/ }))
    expect(screen.getByLabelText('elegido')).toHaveTextContent('3')
    expect(caja()).toHaveValue('Lucía Núñez')
  })

  it('elige con el teclado', () => {
    render(<Probar />)
    fireEvent.change(caja(), { target: { value: 'lu' } })
    fireEvent.keyDown(caja(), { key: 'ArrowDown' })
    fireEvent.keyDown(caja(), { key: 'Enter' })
    expect(screen.getByLabelText('elegido')).toHaveTextContent('3')
  })

  it('al escribir de nuevo se pierde la elección anterior', () => {
    render(<Probar inicial="2" />)
    expect(caja()).toHaveValue('Luis Gómez')
    fireEvent.change(caja(), { target: { value: 'Luis G' } })
    expect(screen.getByLabelText('elegido')).toHaveTextContent('')
    expect(caja()).toHaveValue('Luis G') // lo que se está escribiendo no se borra
  })

  it('si el formulario limpia el valor desde fuera, el texto se vacía', () => {
    function Con() {
      const [v, setV] = useState('2')
      return (
        <>
          <ComboField label="Persona" options={personas} value={v} onChange={setV} />
          <button onClick={() => setV('')}>Limpiar</button>
        </>
      )
    }
    render(<Con />)
    expect(caja()).toHaveValue('Luis Gómez')
    fireEvent.click(screen.getByRole('button', { name: 'Limpiar' }))
    expect(caja()).toHaveValue('')
  })

  it('Escape cierra la lista', () => {
    render(<Probar />)
    fireEvent.focus(caja())
    expect(opciones()).toHaveLength(3)
    fireEvent.keyDown(caja(), { key: 'Escape' })
    expect(opciones()).toHaveLength(0)
  })
})

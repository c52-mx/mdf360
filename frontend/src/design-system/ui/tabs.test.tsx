import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Tabs } from './tabs'

const pestanas = [
  { id: 'a', titulo: 'General', contenido: <p>Contenido general</p> },
  { id: 'b', titulo: 'Contacto', contenido: <p>Contenido de contacto</p> },
  { id: 'c', titulo: 'Iglesia', contenido: <p>Contenido de iglesia</p> },
]

describe('Tabs', () => {
  it('abre la primera pestaña y solo muestra su contenido', () => {
    render(<Tabs titulo="Ficha" pestanas={pestanas} />)
    expect(screen.getByRole('tab', { name: 'General' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('Contenido general')).toBeInTheDocument()
    expect(screen.queryByText('Contenido de contacto')).not.toBeInTheDocument()
  })

  it('cambia de pestaña con el clic, en cualquier orden', () => {
    render(<Tabs titulo="Ficha" pestanas={pestanas} />)
    fireEvent.click(screen.getByRole('tab', { name: 'Iglesia' }))
    expect(screen.getByText('Contenido de iglesia')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Contacto' }))
    expect(screen.getByText('Contenido de contacto')).toBeInTheDocument()
  })

  it('se mueve con flechas, Inicio y Fin y pasa el foco', () => {
    render(<Tabs titulo="Ficha" pestanas={pestanas} />)
    fireEvent.keyDown(screen.getByRole('tab', { name: 'General' }), { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: 'Contacto' })).toHaveFocus()
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Contacto' }), { key: 'End' })
    expect(screen.getByText('Contenido de iglesia')).toBeInTheDocument()
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Iglesia' }), { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: 'General' })).toHaveFocus() // da la vuelta
  })

  it('la pestaña activa es la única en el orden de tabulación', () => {
    render(<Tabs titulo="Ficha" pestanas={pestanas} inicial="b" />)
    expect(screen.getByRole('tab', { name: 'Contacto' })).toHaveAttribute('tabindex', '0')
    expect(screen.getByRole('tab', { name: 'General' })).toHaveAttribute('tabindex', '-1')
  })
})

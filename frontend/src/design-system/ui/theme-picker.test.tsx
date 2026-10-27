import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { ThemePicker } from './theme-picker'

describe('ThemePicker', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-tema')
  })

  it('aplica la paleta elegida a toda la aplicación y la recuerda', () => {
    render(<ThemePicker />)
    expect(screen.getByRole('radio', { name: 'Morado' })).toBeChecked()
    fireEvent.click(screen.getByRole('radio', { name: 'Azul' }))
    expect(document.documentElement.getAttribute('data-tema')).toBe('azul')
    expect(localStorage.getItem('mdf360.tema')).toBe('azul')
    expect(screen.getByRole('radio', { name: 'Azul' })).toBeChecked()
  })

  it('volver al morado quita el atributo', () => {
    localStorage.setItem('mdf360.tema', 'verde')
    render(<ThemePicker />)
    expect(screen.getByRole('radio', { name: 'Verde' })).toBeChecked()
    fireEvent.click(screen.getByRole('radio', { name: 'Morado' }))
    expect(document.documentElement.hasAttribute('data-tema')).toBe(false)
  })
})

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Field } from './field'

describe('Field', () => {
  it('la contraseña se puede mostrar y ocultar', () => {
    render(<Field label="PIN" type="password" defaultValue="482915" />)
    const campo = screen.getByLabelText('PIN')
    expect(campo).toHaveAttribute('type', 'password')
    fireEvent.click(screen.getByRole('button', { name: 'Mostrar contraseña' }))
    expect(campo).toHaveAttribute('type', 'text')
    fireEvent.click(screen.getByRole('button', { name: 'Ocultar contraseña' }))
    expect(campo).toHaveAttribute('type', 'password')
  })

  it('los campos normales no llevan botón de mostrar', () => {
    render(<Field label="Nombre" />)
    expect(screen.queryByRole('button')).toBeNull()
  })
})

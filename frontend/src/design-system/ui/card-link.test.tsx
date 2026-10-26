import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { CardLink } from './card-link'

describe('CardLink', () => {
  it('es un enlace real con respuesta al tocar', () => {
    render(
      <MemoryRouter>
        <CardLink to="/grupos/3">Conexión Norte</CardLink>
      </MemoryRouter>,
    )
    const enlace = screen.getByRole('link', { name: 'Conexión Norte' })
    expect(enlace).toHaveAttribute('href', '/grupos/3')
    expect(enlace).toHaveClass('presionable')
  })
})

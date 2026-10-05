import { render, screen } from '@testing-library/react'
import { Button } from './button'

describe('Button', () => {
  it('muestra su texto y es accesible como botón', () => {
    render(<Button>Guardar lista</Button>)
    expect(screen.getByRole('button', { name: 'Guardar lista' })).toBeInTheDocument()
  })

  it('usa la variante primaria por defecto', () => {
    render(<Button>Aceptar</Button>)
    expect(screen.getByRole('button')).toHaveClass('bg-primary')
  })
})

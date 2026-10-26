import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ConfirmButton } from './confirm-button'

describe('ConfirmButton', () => {
  it('no ejecuta nada al primer toque: pide confirmar', () => {
    const onConfirm = vi.fn()
    render(<ConfirmButton onConfirm={onConfirm}>Descartar</ConfirmButton>)
    fireEvent.click(screen.getByRole('button', { name: 'Descartar' }))
    expect(onConfirm).not.toHaveBeenCalled()
    expect(screen.getByText('¿Seguro?')).toBeInTheDocument()
  })

  it('ejecuta solo al confirmar', () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmButton onConfirm={onConfirm} etiquetaConfirmar="Sí, descartar">
        Descartar
      </ConfirmButton>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Descartar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Sí, descartar' }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Descartar' })).toBeInTheDocument()
  })

  it('se puede cancelar sin ejecutar', () => {
    const onConfirm = vi.fn()
    render(<ConfirmButton onConfirm={onConfirm}>Descartar</ConfirmButton>)
    fireEvent.click(screen.getByRole('button', { name: 'Descartar' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(onConfirm).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Descartar' })).toBeInTheDocument()
  })
})

import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ToastProvider, useToast } from './toast'

function Disparador({ onUndo, ms }: { onUndo?: () => void; ms?: number }) {
  const toast = useToast()
  return (
    <button
      onClick={() =>
        toast.mostrar('Hecho.', onUndo ? { etiqueta: 'Deshacer', onClick: onUndo } : undefined, ms)
      }
    >
      Probar
    </button>
  )
}

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('Toast', () => {
  it('muestra el aviso en una región anunciada y lo quita solo', () => {
    render(
      <ToastProvider>
        <Disparador ms={3000} />
      </ToastProvider>,
    )
    fireEvent.click(screen.getByText('Probar'))
    expect(screen.getByRole('status')).toHaveTextContent('Hecho.')
    act(() => {
      vi.advanceTimersByTime(3100)
    })
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('«Deshacer» ejecuta la acción y cierra el aviso', () => {
    const deshacer = vi.fn()
    render(
      <ToastProvider>
        <Disparador onUndo={deshacer} />
      </ToastProvider>,
    )
    fireEvent.click(screen.getByText('Probar'))
    fireEvent.click(screen.getByRole('button', { name: 'Deshacer' }))
    expect(deshacer).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('status')).toBeNull()
  })

  it('el aviso dura lo bastante para alcanzar a deshacer (8 s por defecto)', () => {
    render(
      <ToastProvider>
        <Disparador onUndo={() => {}} />
      </ToastProvider>,
    )
    fireEvent.click(screen.getByText('Probar'))
    act(() => {
      vi.advanceTimersByTime(7000)
    })
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})

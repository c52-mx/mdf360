import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Collapsible } from './collapsible'
import { DangerAction, DangerZone } from './danger-zone'
import { LineChart } from './line-chart'
import { Modal } from './modal'

describe('Modal', () => {
  it('no dibuja nada cuando está cerrado', () => {
    render(
      <Modal open={false} onClose={() => {}} title="Nuevo aviso">
        <p>Contenido</p>
      </Modal>,
    )
    expect(screen.queryByText('Contenido')).not.toBeInTheDocument()
  })

  it('muestra título y contenido y se cierra con el botón y con Escape', () => {
    const onClose = vi.fn()
    render(
      <Modal open onClose={onClose} title="Nuevo aviso">
        <p>Contenido</p>
      </Modal>,
    )
    expect(screen.getByRole('dialog', { name: 'Nuevo aviso' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar' }))
    fireEvent(screen.getByRole('dialog'), new Event('cancel', { cancelable: true }))
    expect(onClose).toHaveBeenCalledTimes(2)
  })
})

describe('Collapsible', () => {
  it('arranca cerrado, no dibuja el contenido y lo abre al tocar', () => {
    const onToggle = vi.fn()
    render(
      <Collapsible title="Peticiones" summary="3 activas" onToggle={onToggle}>
        <p>Detalle reservado</p>
      </Collapsible>,
    )
    const boton = screen.getByRole('button', { name: /Peticiones/ })
    expect(boton).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByText('Detalle reservado')).not.toBeInTheDocument()
    fireEvent.click(boton)
    expect(boton).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Detalle reservado')).toBeInTheDocument()
    expect(onToggle).toHaveBeenCalledWith(true)
  })
})

describe('DangerZone', () => {
  it('agrupa las acciones de riesgo bajo su título', () => {
    render(
      <DangerZone>
        <DangerAction title="Suspender el grupo" description="Deja de aparecer en las listas.">
          <button>Suspender</button>
        </DangerAction>
      </DangerZone>,
    )
    expect(screen.getByRole('region', { name: 'Zona de riesgo' })).toBeInTheDocument()
    expect(screen.getByText('Suspender el grupo')).toBeInTheDocument()
  })
})

describe('LineChart', () => {
  const series = [
    { nombre: 'Atendidas', puntos: [{ etiqueta: 'Sep', valor: 4 }, { etiqueta: 'Oct', valor: 9 }] },
    { nombre: 'Pendientes', puntos: [{ etiqueta: 'Sep', valor: 7 }, { etiqueta: 'Oct', valor: null }] },
  ]

  it('dibuja la gráfica con leyenda y una tabla de apoyo con los valores', () => {
    render(<LineChart titulo="Peticiones por mes" series={series} />)
    expect(screen.getByRole('img', { name: 'Peticiones por mes' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Series' })).toHaveTextContent('Atendidas')
    expect(screen.getByRole('row', { name: /Oct 9 –/ })).toBeInTheDocument()
  })

  it('un hueco corta la línea y no se dibuja el punto', () => {
    const { container } = render(<LineChart titulo="t" series={series} />)
    expect(container.querySelectorAll('circle')).toHaveLength(3)
  })

  it('sin datos lo dice en vez de mostrar una gráfica vacía', () => {
    render(<LineChart titulo="Vacía" series={[{ nombre: 'A', puntos: [{ etiqueta: 'Sep', valor: null }] }]} />)
    expect(screen.getByText('Aún no hay datos para mostrar.')).toBeInTheDocument()
  })
})

import { fireEvent, render, screen } from '@testing-library/react'
import { Home } from 'lucide-react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { AppShell } from './app-shell'

const nav = [{ to: '/', label: 'Inicio', icon: Home }]

function montar() {
  render(
    <MemoryRouter>
      <AppShell nav={nav}>contenido</AppShell>
    </MemoryRouter>,
  )
}

describe('AppShell', () => {
  beforeEach(() => localStorage.clear())

  it('oculta y muestra el menú lateral y recuerda la preferencia', () => {
    montar()
    expect(document.getElementById('menu-lateral')).not.toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Ocultar menú' }))
    expect(document.getElementById('menu-lateral')).toBeNull()
    expect(localStorage.getItem('mdf360.menu-oculto')).toBe('1')
    fireEvent.click(screen.getByRole('button', { name: 'Mostrar menú' }))
    expect(document.getElementById('menu-lateral')).not.toBeNull()
  })

  it('arranca oculto si así se dejó la última vez', () => {
    localStorage.setItem('mdf360.menu-oculto', '1')
    montar()
    expect(document.getElementById('menu-lateral')).toBeNull()
  })
})

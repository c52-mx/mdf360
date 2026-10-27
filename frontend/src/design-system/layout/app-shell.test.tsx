import { fireEvent, render, screen } from '@testing-library/react'
import { Home, Users } from 'lucide-react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
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

  it('la barra superior muestra quién entró y cierra la sesión', () => {
    const salir = vi.fn()
    render(
      <MemoryRouter>
        <AppShell nav={nav} userName="Ana López" onLogout={salir}>
          contenido
        </AppShell>
      </MemoryRouter>,
    )
    expect(screen.getByText('Ana López')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    expect(salir).toHaveBeenCalledOnce()
  })

  it('el menú lateral agrupa las opciones por categoría', () => {
    render(
      <MemoryRouter>
        <AppShell
          nav={[
            { to: '/', label: 'Inicio', icon: Home },
            { to: '/personas', label: 'Personas', icon: Users, group: 'Catálogos' },
          ]}
        >
          contenido
        </AppShell>
      </MemoryRouter>,
    )
    expect(screen.getByText('Catálogos')).toBeInTheDocument()
  })
})

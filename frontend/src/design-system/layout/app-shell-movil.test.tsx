import { fireEvent, render, screen, within } from '@testing-library/react'
import { Bell, Home, Settings, UserCog, Users, UsersRound } from 'lucide-react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { AppShell } from './app-shell'

const seis = [
  { to: '/', label: 'Inicio', icon: Home },
  { to: '/grupos', label: 'Grupos', icon: UsersRound },
  { to: '/avisos', label: 'Avisos', icon: Bell },
  { to: '/personas', label: 'Personas', icon: Users },
  { to: '/configuracion', label: 'Configuración', icon: Settings },
  { to: '/cuenta', label: 'Mi cuenta', icon: UserCog },
]

function montar(nav = seis, ruta = '/') {
  render(
    <MemoryRouter initialEntries={[ruta]}>
      <AppShell nav={nav}>contenido</AppShell>
    </MemoryRouter>,
  )
}

beforeEach(() => localStorage.clear())

describe('AppShell en el celular', () => {
  it('con más de 5 opciones muestra 4 y un botón «Más» con el resto', () => {
    montar()
    const barra = screen.getAllByRole('navigation', { name: 'Principal' }).at(-1)!
    const enBarra = within(barra)
      .getAllByRole('link')
      .map((a) => a.textContent)
    expect(enBarra).toEqual(['Inicio', 'Grupos', 'Avisos', 'Personas'])
    expect(within(barra).getByRole('button', { name: 'Más' })).toBeInTheDocument()
  })

  it('«Más» abre una hoja con las demás opciones, incluida «Mi cuenta»', () => {
    montar()
    fireEvent.click(screen.getByRole('button', { name: 'Más' }))
    const hoja = screen.getByRole('navigation', { name: 'Más opciones', hidden: true })
    const enlaces = within(hoja).getAllByRole('link', { hidden: true })
    expect(enlaces.map((a) => a.textContent)).toEqual(['Configuración', 'Mi cuenta'])
  })

  it('con 5 opciones o menos no hay botón «Más»', () => {
    montar(seis.slice(0, 5))
    expect(screen.queryByRole('button', { name: 'Más' })).toBeNull()
  })

  it('«Más» se marca activo cuando la pantalla actual está en la hoja', () => {
    montar(seis, '/cuenta')
    expect(screen.getByRole('button', { name: 'Más' })).toHaveClass('text-primary')
  })

  it('al elegir una opción de la hoja se cierra', () => {
    montar()
    const mas = screen.getByRole('button', { name: 'Más' })
    fireEvent.click(mas)
    expect(mas).toHaveAttribute('aria-expanded', 'true')
    const hoja = screen.getByRole('navigation', { name: 'Más opciones', hidden: true })
    fireEvent.click(within(hoja).getByRole('link', { name: 'Mi cuenta', hidden: true }))
    expect(mas).toHaveAttribute('aria-expanded', 'false')
  })

  it('los ítems de módulo muestran su ícono real, no un cuadro vacío', () => {
    montar(seis.map((n) => ({ ...n, module: 'grupos' as const })).slice(0, 3))
    const lateral = screen.getAllByRole('navigation', { name: 'Principal' })[0]
    for (const enlace of within(lateral).getAllByRole('link')) {
      expect(enlace.querySelector('svg')).not.toBeNull()
    }
  })
})

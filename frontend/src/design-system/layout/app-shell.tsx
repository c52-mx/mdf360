import { Ellipsis, PanelLeftClose, PanelLeftOpen, X, type LucideIcon } from 'lucide-react'
import { useRef, useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { moduleBg, type ModuleKey } from './module'
import { cn } from '@/lib/cn'

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  module?: ModuleKey
}

interface AppShellProps {
  nav: NavItem[]
  children: ReactNode
}

const CLAVE_MENU = 'mdf360.menu-oculto'
/** En el celular caben 5 opciones. Si hay más: 4 principales y «Más» con el resto. */
const MAX_BARRA = 5

function leerOculto(): boolean {
  try {
    return localStorage.getItem(CLAVE_MENU) === '1'
  } catch {
    return false
  }
}

/**
 * Estructura común de todas las pantallas (plantilla de administración):
 * menú lateral en escritorio (se puede ocultar y mostrar), barra inferior en móvil con el menú
 * «Más» cuando hay más opciones de las que caben, y un área de contenido con ancho máximo.
 */
export function AppShell({ nav, children }: AppShellProps) {
  const [oculto, setOculto] = useState(leerOculto)
  const [masAbierto, setMasAbierto] = useState(false)
  const hoja = useRef<HTMLDialogElement>(null)
  const { pathname } = useLocation()

  const alternar = () => {
    setOculto((actual) => {
      try {
        localStorage.setItem(CLAVE_MENU, actual ? '0' : '1')
      } catch {
        // sin almacenamiento: el menú funciona igual, solo no recuerda la preferencia
      }
      return !actual
    })
  }
  const Icono = oculto ? PanelLeftOpen : PanelLeftClose

  const hayMas = nav.length > MAX_BARRA
  const principales = hayMas ? nav.slice(0, MAX_BARRA - 1) : nav
  const resto = hayMas ? nav.slice(MAX_BARRA - 1) : []
  const restoActivo = resto.some((n) => (n.to === '/' ? pathname === '/' : pathname.startsWith(n.to)))

  const abrirMas = () => {
    const d = hoja.current
    if (!d) return
    if (typeof d.showModal === 'function') d.showModal()
    else d.setAttribute('open', '')
    setMasAbierto(true)
  }
  const cerrarMas = () => {
    const d = hoja.current
    if (!d) return
    if (typeof d.close === 'function') d.close()
    else d.removeAttribute('open')
    setMasAbierto(false)
  }

  const claseBarra = (activo: boolean) =>
    cn(
      'presionable flex h-16 flex-1 flex-col items-center justify-center gap-0.5 text-xs',
      activo ? 'font-bold text-primary' : 'text-muted-foreground',
    )

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {!oculto ? (
        <aside
          id="menu-lateral"
          className="hidden w-64 shrink-0 flex-col gap-1 bg-foreground p-4 text-background md:flex"
        >
          <div className="mb-4 rounded-card bg-card p-3">
            <img src="/logo.png" alt="Mundo de Fe México" className="h-auto w-full" />
          </div>
          <nav aria-label="Principal" className="flex flex-col gap-1">
            {nav.map(({ to, label, icon: Icon, module }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  cn(
                    'presionable flex h-12 items-center gap-3 rounded-control px-3 font-semibold',
                    isActive ? 'bg-muted-foreground/40' : 'hover:bg-muted-foreground/25',
                  )
                }
              >
                {module ? (
                  <span aria-hidden className={cn('size-5 rounded', moduleBg[module])} />
                ) : (
                  <Icon aria-hidden className="size-5" />
                )}
                {label}
              </NavLink>
            ))}
          </nav>
        </aside>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="hidden px-4 pt-4 md:flex md:px-8">
          <button
            type="button"
            onClick={alternar}
            aria-expanded={!oculto}
            aria-controls="menu-lateral"
            className="presionable flex h-11 items-center gap-2 rounded-control px-3 font-semibold text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <Icono aria-hidden className="size-6" />
            {oculto ? 'Mostrar menú' : 'Ocultar menú'}
          </button>
        </div>
        <main className="mx-auto w-full max-w-6xl flex-1 p-4 pb-[calc(6rem+env(safe-area-inset-bottom))] md:p-8">
          {children}
        </main>
      </div>

      <nav
        aria-label="Principal"
        className="fixed inset-x-0 bottom-0 flex border-t border-border bg-card pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {principales.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => claseBarra(isActive)}>
            <Icon aria-hidden className="size-6" />
            {label}
          </NavLink>
        ))}
        {hayMas ? (
          <button
            type="button"
            onClick={abrirMas}
            aria-haspopup="dialog"
            aria-expanded={masAbierto}
            className={claseBarra(restoActivo)}
          >
            <Ellipsis aria-hidden className="size-6" />
            Más
          </button>
        ) : null}
      </nav>

      {hayMas ? (
        <dialog
          ref={hoja}
          aria-label="Más opciones"
          onClose={() => setMasAbierto(false)}
          onClick={(e) => {
            if (e.target === hoja.current) cerrarMas() // toque en el fondo
          }}
          className="hoja mx-0 mb-0 mt-auto w-full max-w-none rounded-t-card bg-card p-0 text-card-foreground backdrop:bg-foreground/40"
        >
          <div className="flex items-center justify-between px-4 pt-3">
            <span className="font-display text-lg font-bold">Más opciones</span>
            <button
              type="button"
              onClick={cerrarMas}
              aria-label="Cerrar"
              className="presionable flex size-12 items-center justify-center rounded-control hover:bg-muted"
            >
              <X aria-hidden className="size-6" />
            </button>
          </div>
          <nav aria-label="Más opciones" className="flex flex-col px-2 pb-[calc(1rem+env(safe-area-inset-bottom))]">
            {resto.map(({ to, label, icon: Icon, module }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                onClick={cerrarMas}
                className={({ isActive }) =>
                  cn(
                    'presionable flex h-14 items-center gap-3 rounded-control px-3 text-lg font-semibold',
                    isActive ? 'bg-primary-soft text-primary' : 'hover:bg-muted',
                  )
                }
              >
                {module ? (
                  <span aria-hidden className={cn('size-5 rounded', moduleBg[module])} />
                ) : (
                  <Icon aria-hidden className="size-6" />
                )}
                {label}
              </NavLink>
            ))}
          </nav>
        </dialog>
      ) : null}
    </div>
  )
}

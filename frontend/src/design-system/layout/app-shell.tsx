import { Ellipsis, LogOut, PanelLeftClose, PanelLeftOpen, X, type LucideIcon } from 'lucide-react'
import { useRef, useState, type ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { moduleText, type ModuleKey } from './module'
import { cn } from '@/lib/cn'

/** Ícono del menú: siempre el glifo real; los módulos lo llevan en una pastilla con su color. */
function NavIcon({ icon: Icon, module }: { icon: LucideIcon; module?: ModuleKey }) {
  if (!module) return <Icon aria-hidden className="size-6 shrink-0" />
  return (
    <span
      aria-hidden
      className="flex size-8 shrink-0 items-center justify-center rounded-control bg-card ring-1 ring-border"
    >
      <Icon className={cn('size-5', moduleText[module])} />
    </span>
  )
}

export interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  module?: ModuleKey
  /** Categoría del menú (ej. «Operación»). Las opciones consecutivas con la misma se agrupan. */
  group?: string
}

interface AppShellProps {
  nav: NavItem[]
  children: ReactNode
  /** Nombre de quien tiene la sesión abierta; se muestra en la barra superior. */
  userName?: string
  /** Cierra la sesión. Si no se da, la barra superior no muestra el botón. */
  onLogout?: () => void
}

/** Parte el menú en bloques por categoría, conservando el orden. */
function agrupar(items: NavItem[]): { group?: string; items: NavItem[] }[] {
  const bloques: { group?: string; items: NavItem[] }[] = []
  for (const item of items) {
    const ultimo = bloques[bloques.length - 1]
    if (ultimo && ultimo.group === item.group) ultimo.items.push(item)
    else bloques.push({ group: item.group, items: [item] })
  }
  return bloques
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
export function AppShell({ nav, children, userName, onLogout }: AppShellProps) {
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
            {agrupar(nav).map((bloque, i) => (
              <div key={bloque.group ?? `bloque-${i}`} className="flex flex-col gap-1">
                {bloque.group ? (
                  <p className="mt-3 px-3 text-xs font-bold uppercase tracking-wide text-background/60">
                    {bloque.group}
                  </p>
                ) : null}
                {bloque.items.map(({ to, label, icon: Icon, module }) => (
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
                    <NavIcon icon={Icon} module={module} />
                    {label}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
        </aside>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-border bg-card px-4 py-2 md:px-8">
          <button
            type="button"
            onClick={alternar}
            aria-expanded={!oculto}
            aria-controls="menu-lateral"
            className="presionable hidden h-11 items-center gap-2 rounded-control px-3 font-semibold text-muted-foreground hover:bg-muted hover:text-foreground md:flex"
          >
            <Icono aria-hidden className="size-6" />
            {oculto ? 'Mostrar menú' : 'Ocultar menú'}
          </button>
          <img src="/logo.png" alt="Mundo de Fe México" className="h-9 w-auto md:hidden" />
          <div className="flex items-center gap-3">
            {userName ? (
              <span className="hidden max-w-48 truncate font-semibold sm:block">{userName}</span>
            ) : null}
            {onLogout ? (
              <button
                type="button"
                onClick={onLogout}
                className="presionable flex h-11 items-center gap-2 rounded-control px-3 font-semibold text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <LogOut aria-hidden className="size-5" />
                Cerrar sesión
              </button>
            ) : null}
          </div>
        </header>
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
            {agrupar(resto).map((bloque, i) => (
              <div key={bloque.group ?? `resto-${i}`} className="flex flex-col">
                {bloque.group ? (
                  <p className="mt-2 px-3 text-sm font-bold uppercase tracking-wide text-muted-foreground">
                    {bloque.group}
                  </p>
                ) : null}
                {bloque.items.map(({ to, label, icon: Icon, module }) => (
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
                    <NavIcon icon={Icon} module={module} />
                    {label}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
        </dialog>
      ) : null}
    </div>
  )
}

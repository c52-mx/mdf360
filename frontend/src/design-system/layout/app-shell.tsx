import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
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

/**
 * Estructura común de todas las pantallas (plantilla de administración):
 * menú lateral en escritorio, barra inferior en móvil y un área de contenido con ancho máximo.
 */
export function AppShell({ nav, children }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="hidden w-64 shrink-0 flex-col gap-1 bg-foreground p-4 text-background md:flex">
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
                  'flex h-12 items-center gap-3 rounded-control px-3 font-semibold',
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

      <main className="mx-auto w-full max-w-6xl flex-1 p-4 pb-24 md:p-8 md:pb-8">{children}</main>

      <nav
        aria-label="Principal"
        className="fixed inset-x-0 bottom-0 flex border-t border-border bg-card md:hidden"
      >
        {nav.slice(0, 5).map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex h-16 flex-1 flex-col items-center justify-center gap-0.5 text-xs',
                isActive ? 'font-bold text-primary' : 'text-muted-foreground',
              )
            }
          >
            <Icon aria-hidden className="size-6" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

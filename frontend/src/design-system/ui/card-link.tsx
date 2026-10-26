import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/cn'

interface CardLinkProps {
  to: string
  children: ReactNode
  className?: string
}

/** Tarjeta que es un enlace: responde al instante al tocarla (no solo al pasar el cursor). */
export function CardLink({ to, children, className }: CardLinkProps) {
  return (
    <Link
      to={to}
      className={cn(
        'presionable block rounded-card border border-border bg-card p-4 text-card-foreground hover:bg-primary-soft',
        className,
      )}
    >
      {children}
    </Link>
  )
}

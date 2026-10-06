import type { ReactNode } from 'react'
import { Card, CardDescription, CardTitle } from '../ui/card'

interface AuthLayoutProps {
  title: string
  description?: string
  children: ReactNode
}

/** Estructura de las pantallas públicas (entrar, activar, recuperar): logo y tarjeta centrada. */
export function AuthLayout({ title, description, children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="flex w-full max-w-md flex-col gap-6">
        <img src="/logo.png" alt="Mundo de Fe México" className="mx-auto h-auto w-64" />
        <Card className="flex flex-col gap-5 p-6">
          <div className="flex flex-col gap-1">
            <CardTitle className="text-2xl">{title}</CardTitle>
            {description ? <CardDescription className="text-base">{description}</CardDescription> : null}
          </div>
          {children}
        </Card>
      </div>
    </div>
  )
}

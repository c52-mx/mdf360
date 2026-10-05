import { cva, type VariantProps } from 'class-variance-authority'
import { CircleCheck, Info, OctagonAlert, TriangleAlert, type LucideIcon } from 'lucide-react'
import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

const alertVariants = cva('flex items-start gap-3 rounded-control p-3 text-base', {
  variants: {
    tone: {
      info: 'bg-primary-soft text-foreground',
      success: 'bg-success-soft text-success',
      warning: 'bg-warning-soft text-warning',
      destructive: 'bg-destructive-soft text-destructive',
    },
  },
  defaultVariants: { tone: 'info' },
})

const icons: Record<NonNullable<VariantProps<typeof alertVariants>['tone']>, LucideIcon> = {
  info: Info,
  success: CircleCheck,
  warning: TriangleAlert,
  destructive: OctagonAlert,
}

export interface AlertProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {}

/** Mensaje destacado. Siempre lleva icono y texto: el color nunca va solo. */
export function Alert({ className, tone = 'info', children, ...props }: AlertProps) {
  const Icon = icons[tone ?? 'info']
  const urgent = tone === 'destructive' || tone === 'warning'
  return (
    <div
      role={urgent ? 'alert' : 'status'}
      className={cn(alertVariants({ tone }), className)}
      {...props}
    >
      <Icon aria-hidden className="mt-0.5 size-5 shrink-0" />
      <div className="font-semibold">{children}</div>
    </div>
  )
}

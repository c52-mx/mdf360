import { cva, type VariantProps } from 'class-variance-authority'
import type { HTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

const badgeVariants = cva(
  'inline-flex items-center gap-1 rounded-full px-3 py-1 text-sm font-bold',
  {
    variants: {
      tone: {
        neutral: 'bg-muted text-foreground',
        primary: 'bg-primary-soft text-primary',
        success: 'bg-success-soft text-success',
        warning: 'bg-warning-soft text-warning',
        destructive: 'bg-destructive-soft text-destructive',
      },
    },
    defaultVariants: { tone: 'neutral' },
  },
)

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

/** Estado corto. El color nunca va solo: incluye siempre texto (y, si aplica, un icono). */
export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />
}

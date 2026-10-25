import { cn } from '@/lib/cn'

interface MeterProps {
  /** 0 a 100. Si es null se muestra «sin datos». */
  value: number | null
  label: string
  tone?: 'primary' | 'success' | 'warning' | 'destructive'
  className?: string
}

const tones = {
  primary: 'bg-primary',
  success: 'bg-success',
  warning: 'bg-warning',
  destructive: 'bg-destructive',
}

/** Barra de porcentaje con su valor escrito (nunca solo color ni solo forma). */
export function Meter({ value, label, tone = 'success', className }: MeterProps) {
  const ancho = value === null ? 0 : Math.max(0, Math.min(100, value))
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-bold">{value === null ? 'Sin datos' : `${value}%`}</span>
      </div>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value ?? undefined}
        className="h-3 overflow-hidden rounded-full bg-muted"
      >
        <div className={cn('h-full rounded-full', tones[tone])} style={{ width: `${ancho}%` }} />
      </div>
    </div>
  )
}

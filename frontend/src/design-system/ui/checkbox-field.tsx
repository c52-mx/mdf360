import { useId, type InputHTMLAttributes, type ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface CheckboxFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: ReactNode
}

/** Casilla grande, fácil de tocar, con su texto como etiqueta. */
export function CheckboxField({ label, className, id, ...props }: CheckboxFieldProps) {
  const autoId = useId()
  const inputId = id ?? autoId
  return (
    <label htmlFor={inputId} className={cn('flex min-h-12 items-center gap-3', className)}>
      <input
        id={inputId}
        type="checkbox"
        className="size-6 shrink-0 accent-primary"
        {...props}
      />
      <span>{label}</span>
    </label>
  )
}

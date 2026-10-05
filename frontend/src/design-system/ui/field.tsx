import { useId, type InputHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  hint?: string
  error?: string
}

/** Campo de formulario completo: etiqueta, entrada, ayuda y error. Úsalo en lugar de <input> sueltos. */
export function Field({ label, hint, error, className, id, ...props }: FieldProps) {
  const autoId = useId()
  const inputId = id ?? autoId
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="font-bold">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          'h-12 rounded-control border-2 bg-card px-4 text-base text-foreground placeholder:text-muted-foreground',
          error ? 'border-destructive' : 'border-border focus:border-primary',
          className,
        )}
        {...props}
      />
      {error ? (
        <p id={`${inputId}-error`} role="alert" className="text-sm font-bold text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={`${inputId}-hint`} className="text-sm text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  )
}

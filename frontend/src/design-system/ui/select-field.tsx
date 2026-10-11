import { useId, type SelectHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  options: { value: string; label: string }[]
  hint?: string
  error?: string
}

/** Lista desplegable con etiqueta, ayuda y error. */
export function SelectField({ label, options, hint, error, className, id, ...props }: SelectFieldProps) {
  const autoId = useId()
  const selectId = id ?? autoId
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={selectId} className="font-bold">
        {label}
      </label>
      <select
        id={selectId}
        aria-invalid={error ? true : undefined}
        className={cn(
          'h-12 rounded-control border-2 bg-card px-3 text-base text-foreground',
          error ? 'border-destructive' : 'border-border focus:border-primary',
          className,
        )}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error ? (
        <p role="alert" className="text-sm font-bold text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p className="text-sm text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  )
}

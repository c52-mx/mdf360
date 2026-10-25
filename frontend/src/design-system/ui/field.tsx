import { Eye, EyeOff } from 'lucide-react'
import { useId, useState, type InputHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  hint?: string
  error?: string
}

/**
 * Campo de formulario completo: etiqueta, entrada, ayuda y error. Úsalo en lugar de <input> sueltos.
 * Los campos de contraseña incluyen un botón para mostrar u ocultar lo que se escribe.
 */
export function Field({ label, hint, error, className, id, type, ...props }: FieldProps) {
  const autoId = useId()
  const inputId = id ?? autoId
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined
  const esPassword = type === 'password'
  const [visible, setVisible] = useState(false)
  const Icono = visible ? EyeOff : Eye

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="font-bold">
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          type={esPassword && visible ? 'text' : type}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            'h-12 w-full rounded-control border-2 bg-card px-4 text-base text-foreground placeholder:text-muted-foreground',
            error ? 'border-destructive' : 'border-border focus:border-primary',
            esPassword && 'pr-14',
            className,
          )}
          {...props}
        />
        {esPassword ? (
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'}
            aria-pressed={visible}
            className="absolute inset-y-0 right-0 flex w-12 items-center justify-center rounded-control text-muted-foreground hover:text-foreground"
          >
            <Icono aria-hidden className="size-6" />
          </button>
        ) : null}
      </div>
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

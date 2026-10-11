import { useId, type TextareaHTMLAttributes } from 'react'
import { cn } from '@/lib/cn'

interface TextareaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string
  hint?: string
}

/** Texto largo con etiqueta. */
export function TextareaField({ label, hint, className, id, ...props }: TextareaFieldProps) {
  const autoId = useId()
  const areaId = id ?? autoId
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={areaId} className="font-bold">
        {label}
      </label>
      <textarea
        id={areaId}
        rows={3}
        className={cn(
          'rounded-control border-2 border-border bg-card px-4 py-3 text-base text-foreground focus:border-primary',
          className,
        )}
        {...props}
      />
      {hint ? <p className="text-sm text-muted-foreground">{hint}</p> : null}
    </div>
  )
}

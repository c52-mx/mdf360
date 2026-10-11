import type { ChangeEvent, ReactNode } from 'react'
import { cn } from '@/lib/cn'

interface FileButtonProps {
  children: ReactNode
  accept?: string
  onFile: (file: File) => void
  disabled?: boolean
}

/** Botón que abre el selector de archivos (en el celular ofrece la cámara). */
export function FileButton({ children, accept = 'image/*', onFile, disabled }: FileButtonProps) {
  const onChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) onFile(file)
    event.target.value = ''
  }
  return (
    <label
      className={cn(
        'inline-flex h-11 cursor-pointer items-center justify-center gap-2 rounded-control border-2 border-primary bg-card px-4 text-base font-bold text-primary hover:bg-primary-soft',
        disabled && 'pointer-events-none opacity-50',
      )}
    >
      {children}
      <input type="file" accept={accept} onChange={onChange} disabled={disabled} className="sr-only" />
    </label>
  )
}

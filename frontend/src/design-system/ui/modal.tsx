import { useEffect, useId, useRef, type ReactNode } from 'react'
import { X } from 'lucide-react'
import { Button } from './button'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: ReactNode
}

/**
 * Ventana para formularios pequeños. Usa <dialog> nativo: el foco queda dentro, Escape la cierra
 * y lo de atrás no se puede tocar. Para formularios largos usa una página o pestañas.
 */
export function Modal({ open, onClose, title, description, children }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) {
      if (typeof dialog.showModal === 'function') dialog.showModal()
      else dialog.setAttribute('open', '')
    } else if (!open && dialog.open) {
      if (typeof dialog.close === 'function') dialog.close()
      else dialog.removeAttribute('open')
    }
  }, [open])

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault()
        onClose()
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose() // toque en el fondo
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-lg rounded-card border border-border bg-card p-0 text-card-foreground shadow-xl backdrop:bg-foreground/50"
    >
      {open ? (
        <div className="flex flex-col gap-4 p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex flex-col gap-1">
              <h2 id={titleId} className="text-xl font-bold">
                {title}
              </h2>
              {description ? <p className="text-muted-foreground">{description}</p> : null}
            </div>
            <Button type="button" variant="ghost" size="sm" aria-label="Cerrar" onClick={onClose}>
              <X aria-hidden className="size-5" />
            </Button>
          </div>
          {children}
        </div>
      ) : null}
    </dialog>
  )
}

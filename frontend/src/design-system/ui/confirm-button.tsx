import { useState, type ReactNode } from 'react'
import { Button, type ButtonProps } from './button'

interface ConfirmButtonProps extends Omit<ButtonProps, 'onClick' | 'children'> {
  children: ReactNode
  /** Pregunta que se muestra al pedir la confirmación. */
  pregunta?: string
  etiquetaConfirmar?: string
  onConfirm: () => void
}

/**
 * Confirmación en dos pasos, en el mismo lugar y sin ventana emergente. Úsalo solo para lo que
 * NO se puede deshacer; para lo demás es mejor avisar con «Deshacer».
 */
export function ConfirmButton({
  children,
  pregunta = '¿Seguro?',
  etiquetaConfirmar = 'Sí, continuar',
  onConfirm,
  ...props
}: ConfirmButtonProps) {
  const [pidiendo, setPidiendo] = useState(false)

  if (!pidiendo) {
    return (
      <Button type="button" {...props} onClick={() => setPidiendo(true)}>
        {children}
      </Button>
    )
  }
  return (
    <span role="group" aria-label={pregunta} className="flex flex-wrap items-center gap-2">
      <span className="font-bold">{pregunta}</span>
      <Button
        type="button"
        size="sm"
        variant="destructive"
        onClick={() => {
          setPidiendo(false)
          onConfirm()
        }}
      >
        {etiquetaConfirmar}
      </Button>
      <Button type="button" size="sm" variant="ghost" onClick={() => setPidiendo(false)}>
        Cancelar
      </Button>
    </span>
  )
}

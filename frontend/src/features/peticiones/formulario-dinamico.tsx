import { CheckboxField, Field, SelectField, TextareaField } from '@/design-system'
import type { Campo, Valores } from './types'

interface Props {
  campos: Campo[]
  valores: Valores
  onChange: (valores: Valores) => void
  disabled?: boolean
}

/**
 * Dibuja un formulario a partir de su definición (campos configurables). Es genérico: lo usan las
 * peticiones de oración y servirá para otros formularios del diseñador (CFG-01).
 */
export function FormularioDinamico({ campos, valores, onChange, disabled }: Props) {
  const cambiar = (clave: string, valor: string | boolean) => onChange({ ...valores, [clave]: valor })

  return (
    <div className="flex flex-col gap-4">
      {campos
        .filter((c) => c.activo)
        .map((c) => {
          const etiqueta = c.requerido ? c.etiqueta : `${c.etiqueta}`
          const valor = valores[c.clave]
          switch (c.tipo) {
            case 'textarea':
              return (
                <TextareaField
                  key={c.clave}
                  label={etiqueta}
                  required={c.requerido}
                  disabled={disabled}
                  value={String(valor ?? '')}
                  onChange={(e) => cambiar(c.clave, e.target.value)}
                />
              )
            case 'seleccion':
              return (
                <SelectField
                  key={c.clave}
                  label={etiqueta}
                  required={c.requerido}
                  disabled={disabled}
                  value={String(valor ?? '')}
                  onChange={(e) => cambiar(c.clave, e.target.value)}
                  options={[
                    { value: '', label: 'Elige una opción' },
                    ...c.opciones.map((o) => ({ value: o, label: o })),
                  ]}
                />
              )
            case 'casilla':
              return (
                <CheckboxField
                  key={c.clave}
                  label={etiqueta}
                  disabled={disabled}
                  checked={Boolean(valor)}
                  onChange={(e) => cambiar(c.clave, e.target.checked)}
                />
              )
            default:
              return (
                <Field
                  key={c.clave}
                  label={etiqueta}
                  required={c.requerido}
                  disabled={disabled}
                  value={String(valor ?? '')}
                  onChange={(e) => cambiar(c.clave, e.target.value)}
                />
              )
          }
        })}
    </div>
  )
}

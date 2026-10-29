import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { CheckboxField, Field, SelectField, TextareaField } from '@/design-system'
import { api } from '@/lib/api'
import type { CampoExtra, Objetivo, Respuestas } from './types'

interface Props {
  campos: CampoExtra[]
  valores: Respuestas
  /** Nombre del registro al que apunta cada campo de relación (para mostrarlo sin buscarlo). */
  etiquetas?: Record<string, string>
  onChange: (valores: Respuestas) => void
  disabled?: boolean
}

/** Dibuja los campos adicionales definidos en el diseñador de formularios. Los desactivados no se muestran. */
export function CamposExtra({ campos, valores, etiquetas = {}, onChange, disabled }: Props) {
  const cambiar = (clave: string, valor: string | boolean | number | null) =>
    onChange({ ...valores, [clave]: valor })

  return (
    <div className="flex flex-col gap-4">
      {campos
        .filter((c) => c.activo)
        .map((c) => {
          const valor = valores[c.clave]
          const comunes = { label: c.etiqueta, hint: c.ayuda || undefined, disabled }
          switch (c.tipo) {
            case 'textarea':
              return (
                <TextareaField
                  key={c.clave}
                  {...comunes}
                  required={c.requerido}
                  value={String(valor ?? '')}
                  onChange={(e) => cambiar(c.clave, e.target.value)}
                />
              )
            case 'numero':
              return (
                <Field
                  key={c.clave}
                  {...comunes}
                  required={c.requerido}
                  inputMode="decimal"
                  value={String(valor ?? '')}
                  onChange={(e) => cambiar(c.clave, e.target.value)}
                />
              )
            case 'fecha':
              return (
                <Field
                  key={c.clave}
                  {...comunes}
                  required={c.requerido}
                  type="date"
                  value={String(valor ?? '')}
                  onChange={(e) => cambiar(c.clave, e.target.value)}
                />
              )
            case 'seleccion':
              return (
                <SelectField
                  key={c.clave}
                  {...comunes}
                  required={c.requerido}
                  value={String(valor ?? '')}
                  onChange={(e) => cambiar(c.clave, e.target.value)}
                  options={[{ value: '', label: 'Elige una opción' }, ...c.opciones.map((o) => ({ value: o, label: o }))]}
                />
              )
            case 'casilla':
              return (
                <CheckboxField
                  key={c.clave}
                  label={c.etiqueta}
                  disabled={disabled}
                  checked={Boolean(valor)}
                  onChange={(e) => cambiar(c.clave, e.target.checked)}
                />
              )
            case 'relacion':
              return (
                <SelectorRelacion
                  key={c.clave}
                  etiqueta={c.etiqueta}
                  ayuda={c.ayuda}
                  objetivo={c.objetivo as Objetivo}
                  valor={valor ? Number(valor) : null}
                  nombreActual={etiquetas[c.clave]}
                  requerido={c.requerido}
                  disabled={disabled}
                  onChange={(id) => cambiar(c.clave, id)}
                />
              )
            default:
              return (
                <Field
                  key={c.clave}
                  {...comunes}
                  required={c.requerido}
                  value={String(valor ?? '')}
                  onChange={(e) => cambiar(c.clave, e.target.value)}
                />
              )
          }
        })}
    </div>
  )
}

interface Opcion {
  id: number
  nombre: string
}

interface RelacionProps {
  etiqueta: string
  ayuda: string
  objetivo: Objetivo
  valor: number | null
  nombreActual?: string
  requerido: boolean
  disabled?: boolean
  onChange: (id: number | null) => void
}

/** Elige un registro (persona, grupo o ministerio); se guarda su id, no su nombre. */
function SelectorRelacion({ etiqueta, ayuda, objetivo, valor, nombreActual, requerido, disabled, onChange }: RelacionProps) {
  const [busqueda, setBusqueda] = useState('')
  const esPersona = objetivo === 'persona'

  const opciones = useQuery({
    queryKey: ['relacion', objetivo, busqueda],
    enabled: !esPersona || busqueda.trim().length >= 2,
    queryFn: async (): Promise<Opcion[]> => {
      if (esPersona) {
        const r = await api<{ results: { id: number; nombre_completo: string }[] }>(
          `/api/personas/?q=${encodeURIComponent(busqueda.trim())}&page_size=8`,
        )
        return r.results.map((p) => ({ id: p.id, nombre: p.nombre_completo }))
      }
      const ruta = objetivo === 'grupo' ? '/api/grupos/' : '/api/unidades/'
      const lista = await api<{ id: number; nombre: string }[]>(ruta)
      return lista.map((x) => ({ id: x.id, nombre: x.nombre }))
    },
  })
  const lista = opciones.data ?? []

  return (
    <div className="flex flex-col gap-2">
      <span className="font-bold">{etiqueta}</span>
      {ayuda ? <span className="text-sm text-muted-foreground">{ayuda}</span> : null}
      {valor ? (
        <div className="flex flex-wrap items-center gap-3">
          <span>{nombreActual ?? lista.find((o) => o.id === valor)?.nombre ?? `Registro ${valor}`}</span>
          {!disabled && !requerido ? (
            <button type="button" className="presionable font-semibold text-primary" onClick={() => onChange(null)}>
              Quitar
            </button>
          ) : null}
        </div>
      ) : null}
      {!disabled ? (
        esPersona ? (
          <>
            <Field
              label={`Buscar ${etiqueta.toLowerCase()}`}
              placeholder="Escribe al menos 2 letras"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
            />
            {lista.length > 0 ? (
              <ul className="flex flex-col gap-1">
                {lista.map((o) => (
                  <li key={o.id}>
                    <button
                      type="button"
                      className="presionable text-left font-semibold text-primary"
                      onClick={() => {
                        onChange(o.id)
                        setBusqueda('')
                      }}
                    >
                      {o.nombre}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        ) : (
          <SelectField
            label={`Elegir ${objetivo === 'grupo' ? 'grupo' : 'ministerio'}`}
            value={valor ? String(valor) : ''}
            onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
            options={[{ value: '', label: 'Elige una opción' }, ...lista.map((o) => ({ value: String(o.id), label: o.nombre }))]}
          />
        )
      ) : null}
    </div>
  )
}

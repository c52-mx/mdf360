import { useId, useMemo, useRef, useState } from 'react'
import { cn } from '@/lib/cn'

export interface ComboOption {
  value: string
  /** Nombre que se muestra y por el que se busca. */
  label: string
  /** Dato secundario por el que también se busca, p. ej. el número de WhatsApp. */
  detalle?: string
}

interface ComboFieldProps {
  label: string
  options: ComboOption[]
  /** Valor elegido ('' = ninguno). */
  value: string
  onChange: (value: string) => void
  placeholder?: string
  hint?: string
  error?: string
  /** Texto cuando nada coincide. */
  vacio?: string
  disabled?: boolean
  /** Avisa lo que se escribe, para pedir al servidor las coincidencias en listas muy largas. */
  onBuscar?: (texto: string) => void
  /** false = las opciones ya vienen filtradas por el servidor (no se vuelven a filtrar aquí). */
  filtrar?: boolean
  /** Para elegir varias personas, una tras otra: al elegir, el campo queda vacío de nuevo. */
  limpiarAlElegir?: boolean
}

/** Sin acentos, mayúsculas, espacios ni signos: «55 1234-5678» y «551234» coinciden. */
const normalizar = (t: string) =>
  t
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]/gu, '')

/**
 * Buscador de personas (y de cualquier lista larga): se escribe parte del nombre o del número y
 * la lista se filtra. Funciona con teclado: flechas, Enter para elegir y Escape para cerrar.
 */
export function ComboField({
  label,
  options,
  value,
  onChange,
  placeholder = 'Escribe un nombre o número',
  hint,
  error,
  vacio = 'Nadie coincide con la búsqueda.',
  disabled,
  onBuscar,
  filtrar = true,
  limpiarAlElegir = false,
}: ComboFieldProps) {
  const id = useId()
  const listaId = `${id}-lista`
  const elegida = options.find((o) => o.value === value)
  const [texto, setTexto] = useState(elegida?.label ?? '')
  const [abierta, setAbierta] = useState(false)
  const [activa, setActiva] = useState(0)
  const caja = useRef<HTMLDivElement>(null)

  // Si el valor cambia desde fuera (p. ej. se limpia el formulario), el texto lo sigue. Lo que la
  // persona teclea no se toca: al escribir, el propio campo ya vació la elección.
  const [previo, setPrevio] = useState(value)
  if (value !== previo) {
    setPrevio(value)
    const nuevo = options.find((o) => o.value === value)?.label
    if (nuevo !== undefined) setTexto(nuevo)
    else if (texto === options.find((o) => o.value === previo)?.label) setTexto('')
  }

  const coincidencias = useMemo(() => {
    const q = normalizar(texto)
    if (!q || elegida?.label === texto || !filtrar) return options.slice(0, 50)
    return options
      .filter((o) => normalizar(`${o.label} ${o.detalle ?? ''}`).includes(q))
      .slice(0, 50)
  }, [options, texto, elegida, filtrar])

  function elegir(o: ComboOption) {
    onChange(o.value)
    setTexto(limpiarAlElegir ? '' : o.label)
    if (limpiarAlElegir) onBuscar?.('')
    setAbierta(false)
  }

  return (
    <div
      ref={caja}
      className="relative flex flex-col gap-1.5"
      onBlur={(e) => {
        if (!caja.current?.contains(e.relatedTarget)) setAbierta(false)
      }}
    >
      <label htmlFor={id} className="font-bold">
        {label}
      </label>
      <input
        id={id}
        role="combobox"
        aria-expanded={abierta}
        aria-controls={listaId}
        aria-autocomplete="list"
        aria-activedescendant={abierta && coincidencias[activa] ? `${id}-${activa}` : undefined}
        aria-invalid={error ? true : undefined}
        autoComplete="off"
        disabled={disabled}
        placeholder={placeholder}
        value={texto}
        className={cn(
          'h-12 rounded-control border-2 bg-card px-3 text-base text-foreground',
          error ? 'border-destructive' : 'border-border focus:border-primary',
        )}
        onFocus={() => setAbierta(true)}
        onChange={(e) => {
          setTexto(e.target.value)
          onBuscar?.(e.target.value)
          setAbierta(true)
          setActiva(0)
          if (value) onChange('') // al escribir se pierde la elección anterior
        }}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') {
            e.preventDefault()
            setAbierta(true)
            setActiva((a) => Math.min(a + 1, coincidencias.length - 1))
          } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setActiva((a) => Math.max(a - 1, 0))
          } else if (e.key === 'Enter' && abierta && coincidencias[activa]) {
            e.preventDefault()
            elegir(coincidencias[activa])
          } else if (e.key === 'Escape') {
            setAbierta(false)
          }
        }}
      />
      {abierta ? (
        <ul
          id={listaId}
          role="listbox"
          aria-label={label}
          className="absolute top-full z-20 mt-1 max-h-60 w-full overflow-auto rounded-control border border-border bg-card shadow-lg"
        >
          {coincidencias.length === 0 ? (
            <li className="px-3 py-3 text-muted-foreground">{vacio}</li>
          ) : (
            coincidencias.map((o, i) => (
              <li
                key={o.value}
                id={`${id}-${i}`}
                role="option"
                aria-selected={o.value === value}
                className={cn(
                  'flex min-h-11 cursor-pointer flex-col justify-center px-3 py-2',
                  i === activa && 'bg-primary-soft',
                )}
                onMouseEnter={() => setActiva(i)}
                onMouseDown={(e) => e.preventDefault()} // no pierde el foco antes del clic
                onClick={() => elegir(o)}
              >
                <span className="font-bold">{o.label}</span>
                {o.detalle ? <span className="text-sm text-muted-foreground">{o.detalle}</span> : null}
              </li>
            ))
          )}
        </ul>
      ) : null}
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

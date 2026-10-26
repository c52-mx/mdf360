import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react'

interface Aviso {
  id: number
  texto: string
  accion?: { etiqueta: string; onClick: () => void }
}

interface ToastApi {
  /** Muestra un aviso breve. Con `accion` ofrece, por ejemplo, «Deshacer». */
  mostrar: (texto: string, accion?: Aviso['accion'], duracionMs?: number) => void
}

const ToastContext = createContext<ToastApi | null>(null)

/**
 * Avisos breves en la parte baja, encima de la barra de navegación. Se anuncian a lectores de
 * pantalla (aria-live) y dejan tiempo suficiente para pulsar «Deshacer».
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([])
  const contador = useRef(0)
  const temporizadores = useRef(new Map<number, number>())

  const cerrar = useCallback((id: number) => {
    window.clearTimeout(temporizadores.current.get(id))
    temporizadores.current.delete(id)
    setAvisos((lista) => lista.filter((a) => a.id !== id))
  }, [])

  const mostrar = useCallback<ToastApi['mostrar']>(
    (texto, accion, duracionMs = 8000) => {
      contador.current += 1
      const id = contador.current
      setAvisos((lista) => [...lista.slice(-2), { id, texto, accion }])
      temporizadores.current.set(id, window.setTimeout(() => cerrar(id), duracionMs))
    },
    [cerrar],
  )

  useEffect(() => {
    const mapa = temporizadores.current
    return () => mapa.forEach((t) => window.clearTimeout(t))
  }, [])

  return (
    <ToastContext.Provider value={{ mostrar }}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-20 z-50 flex flex-col items-center gap-2 px-4 pb-[env(safe-area-inset-bottom)] md:bottom-6"
      >
        {avisos.map((a) => (
          <div
            key={a.id}
            role="status"
            className="pointer-events-auto flex w-full max-w-md items-center justify-between gap-3 rounded-card bg-foreground px-4 py-3 text-background shadow-lg"
          >
            <span>{a.texto}</span>
            {a.accion ? (
              <button
                type="button"
                onClick={() => {
                  a.accion?.onClick()
                  cerrar(a.id)
                }}
                className="presionable h-11 rounded-control px-3 font-bold text-accent hover:underline"
              >
                {a.accion.etiqueta}
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast debe usarse dentro de <ToastProvider>')
  return ctx
}

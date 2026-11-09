import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Alert, Button, Card, CardTitle, TextareaField } from '@/design-system'
import { api } from '@/lib/api'
import { cn } from '@/lib/cn'
import { CLAVE_MURO } from './acciones-publicacion'
import type { Destino } from './types'

const clave = (d: Destino) => `${d.tipo}:${d.id}`

/**
 * Compositor del muro. Solo aparece si la persona puede publicar en alguna audiencia; el servidor
 * vuelve a comprobarlo al publicar. Se elige a quién va dirigida (una o varias).
 */
export function NuevaPublicacion() {
  const queryClient = useQueryClient()
  const [texto, setTexto] = useState('')
  const [elegidas, setElegidas] = useState<string[]>([])
  const destinos = useQuery({
    queryKey: ['muro-destinos'],
    queryFn: () => api<Destino[]>('/api/muro/destinos/'),
  })
  const publicar = useMutation({
    mutationFn: () =>
      api('/api/muro/', {
        method: 'POST',
        body: {
          texto,
          destinos: (destinos.data ?? [])
            .filter((d) => elegidas.includes(clave(d)))
            .map(({ tipo, id }) => ({ tipo, id })),
        },
      }),
    onSuccess: () => {
      setTexto('')
      setElegidas([])
      void queryClient.invalidateQueries({ queryKey: CLAVE_MURO })
    },
  })

  const lista = destinos.data ?? []
  if (lista.length === 0) return null

  const alternar = (d: Destino) =>
    setElegidas((actual) =>
      actual.includes(clave(d)) ? actual.filter((c) => c !== clave(d)) : [...actual, clave(d)],
    )
  const enviar = (e: FormEvent) => {
    e.preventDefault()
    publicar.mutate()
  }

  return (
    <Card>
      <form onSubmit={enviar} className="flex flex-col gap-3">
        <CardTitle>Publicar</CardTitle>
        <TextareaField
          label="¿Qué quieres compartir?"
          maxLength={2000}
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          hint={`${texto.length}/2000`}
        />
        <fieldset className="flex flex-col gap-2">
          <legend className="font-semibold">Dirigida a</legend>
          <div className="flex flex-wrap gap-2">
            {lista.map((d) => {
              const activa = elegidas.includes(clave(d))
              return (
                <button
                  key={clave(d)}
                  type="button"
                  aria-pressed={activa}
                  onClick={() => alternar(d)}
                  className={cn(
                    'presionable flex h-11 items-center rounded-full border px-4 text-sm font-semibold',
                    activa
                      ? 'border-primary bg-primary-soft text-primary'
                      : 'border-border text-muted-foreground hover:bg-muted',
                  )}
                >
                  {d.etiqueta}
                </button>
              )
            })}
          </div>
        </fieldset>
        {publicar.error ? <Alert tone="destructive">{publicar.error.message}</Alert> : null}
        <Button
          type="submit"
          disabled={publicar.isPending || !texto.trim() || elegidas.length === 0}
        >
          Publicar
        </Button>
      </form>
    </Card>
  )
}

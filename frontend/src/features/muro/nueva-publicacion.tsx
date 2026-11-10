import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Alert, Button, Card, CardTitle, CheckboxField, TextareaField } from '@/design-system'
import { api, apiForm } from '@/lib/api'
import { cn } from '@/lib/cn'
import { CLAVE_MURO } from './acciones-publicacion'
import { MAX_FOTOS, type AudienciaFija, type Destino, type Publicacion } from './types'

const clave = (d: Destino) => `${d.tipo}:${d.id}`

/**
 * Compositor del muro. Solo aparece si la persona puede publicar en alguna audiencia; el servidor
 * vuelve a comprobarlo al publicar. Se elige a quién va dirigida (una o varias).
 */
export function NuevaPublicacion({ audiencia }: { audiencia?: AudienciaFija }) {
  const queryClient = useQueryClient()
  const [texto, setTexto] = useState('')
  const [elegidas, setElegidas] = useState<string[]>([])
  const [fotos, setFotos] = useState<File[]>([])
  const [permiso, setPermiso] = useState(false)
  const destinos = useQuery({
    queryKey: ['muro-destinos'],
    queryFn: () => api<Destino[]>('/api/muro/destinos/'),
  })
  const publicar = useMutation({
    mutationFn: async () => {
      const dirigidas = audiencia ? lista : lista.filter((d) => elegidas.includes(clave(d)))
      const creada = await api<Publicacion>('/api/muro/', {
        method: 'POST',
        body: {
          texto,
          destinos: dirigidas.map(({ tipo, id }) => ({ tipo, id })),
        },
      })
      // Las fotos se suben una por una a la publicación ya creada
      try {
        for (const foto of fotos) {
          const form = new FormData()
          form.append('foto', foto)
          form.append('permiso_confirmado', 'true')
          await apiForm(`/api/muro/${creada.id}/fotos/`, form)
        }
      } catch (e) {
        void queryClient.invalidateQueries({ queryKey: CLAVE_MURO })
        throw new Error(
          `La publicación se creó, pero no se pudieron subir todas las fotos: ${
            e instanceof Error ? e.message : ''
          }`,
          { cause: e },
        )
      }
    },
    onSuccess: () => {
      setTexto('')
      setElegidas([])
      setFotos([])
      setPermiso(false)
      void queryClient.invalidateQueries({ queryKey: CLAVE_MURO })
    },
  })

  // En la página de un grupo o ministerio solo se publica ahí: la audiencia ya viene elegida
  const lista = (destinos.data ?? []).filter(
    (d) => !audiencia || (d.tipo === audiencia.tipo && d.id === audiencia.id),
  )
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
        {audiencia ? (
          <p className="text-sm text-muted-foreground">Se publicará en {lista[0].etiqueta}.</p>
        ) : (
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
        )}
        <div className="flex flex-col gap-2">
          <label className="presionable flex h-11 w-fit cursor-pointer items-center rounded-full border border-border px-4 text-sm font-semibold text-muted-foreground hover:bg-muted">
            Agregar fotos
            <input
              type="file"
              accept="image/*"
              multiple
              className="sr-only"
              onChange={(e) => {
                setFotos((actual) =>
                  [...actual, ...Array.from(e.target.files ?? [])].slice(0, MAX_FOTOS),
                )
                e.target.value = ''
              }}
            />
          </label>
          {fotos.length > 0 ? (
            <>
              <ul aria-label="Fotos elegidas" className="flex flex-col gap-1 text-sm">
                {fotos.map((f, i) => (
                  <li key={`${f.name}-${i}`} className="flex items-center justify-between gap-2">
                    <span className="truncate">{f.name}</span>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      aria-label={`Quitar ${f.name}`}
                      onClick={() => setFotos((actual) => actual.filter((_, j) => j !== i))}
                    >
                      Quitar
                    </Button>
                  </li>
                ))}
              </ul>
              <CheckboxField
                checked={permiso}
                onChange={(e) => setPermiso(e.target.checked)}
                label="Confirmo que las personas que aparecen en las fotos (o sus tutores, si son menores de edad) aceptaron que se publiquen."
              />
            </>
          ) : null}
        </div>
        {publicar.error ? <Alert tone="destructive">{publicar.error.message}</Alert> : null}
        <Button
          type="submit"
          disabled={
            publicar.isPending ||
            !texto.trim() ||
            (!audiencia && elegidas.length === 0) ||
            (fotos.length > 0 && !permiso)
          }
        >
          Publicar
        </Button>
      </form>
    </Card>
  )
}

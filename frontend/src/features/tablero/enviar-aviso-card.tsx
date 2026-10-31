import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Megaphone, X } from 'lucide-react'
import { useDeferredValue, useState } from 'react'
import { Alert, Badge, Button, CheckboxField, ComboField, Modal, TextareaField } from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'

interface Destino {
  tipo: string
  tipo_display: string
  id: number
  etiqueta: string
  /** Toda la iglesia, para quien no la publica directo: alguien debe autorizarla. */
  requiere_autorizacion?: boolean
}
interface PersonaFila {
  id: number
  nombre_completo: string
  whatsapp?: string
}
interface Resultado {
  enviados: { tipo: string; id: number; etiqueta: string }[]
  omitidos: { tipo: string; id: number }[]
  pendientes?: { tipo: string; id: number; etiqueta: string }[]
}

const clave = (tipo: string, id: number) => `${tipo}:${id}`

/** Un mismo aviso para varios lugares: toda la iglesia, grupos, ministerios y personas. */
export function EnviarAvisoCard() {
  const queryClient = useQueryClient()
  const puedePersonas = useCan('avisos.personas')
  const [abierto, setAbierto] = useState(false)
  const [texto, setTexto] = useState('')
  const [elegidos, setElegidos] = useState<Record<string, { tipo: string; id: number }>>({})
  const [personas, setPersonas] = useState<Record<number, string>>({})
  const [busqueda, setBusqueda] = useState('')
  const q = useDeferredValue(busqueda.trim())
  const [resultado, setResultado] = useState<Resultado | null>(null)

  const destinos = useQuery({
    queryKey: ['tablero-destinos'],
    queryFn: () => api<Destino[]>('/api/tablero/destinos/'),
  })
  const encontradas = useQuery({
    queryKey: ['personas-aviso', q],
    enabled: puedePersonas && abierto && q.length >= 2,
    queryFn: () => api<{ results: PersonaFila[] }>(`/api/personas/?q=${encodeURIComponent(q)}&page_size=8`),
  })

  const cerrar = () => setAbierto(false)
  const enviar = useMutation({
    mutationFn: () =>
      api<Resultado>('/api/tablero/masivo/', {
        method: 'POST',
        body: {
          texto,
          destinos: [
            ...Object.values(elegidos),
            ...Object.keys(personas).map((id) => ({ tipo: 'persona', id: Number(id) })),
          ],
        },
      }),
    onSuccess: (r) => {
      setResultado(r)
      cerrar()
      setTexto('')
      setElegidos({})
      setPersonas({})
      setBusqueda('')
      void queryClient.invalidateQueries({ queryKey: ['tablero-no-leidos'] })
      void queryClient.invalidateQueries({ queryKey: ['tablero-por-autorizar'] })
    },
  })

  // Quien no puede publicar en ningún lugar ni escribir a personas no ve este botón
  if (!destinos.data || (destinos.data.length === 0 && !puedePersonas)) return null

  const grupos = destinos.data.reduce<Record<string, Destino[]>>((acc, d) => {
    ;(acc[d.tipo_display] ??= []).push(d)
    return acc
  }, {})
  const total = Object.keys(elegidos).length + Object.keys(personas).length
  const opciones = (encontradas.data?.results ?? [])
    .filter((p) => !(p.id in personas))
    .map((p) => ({ value: String(p.id), label: p.nombre_completo, detalle: p.whatsapp }))

  return (
    <div>
      <Button onClick={() => setAbierto(true)}>
        <Megaphone aria-hidden className="size-5" />
        Enviar un aviso
      </Button>
      {resultado ? (
        <Alert tone="success" className="mt-3">
          {resultado.enviados.length > 0
            ? `Aviso enviado a ${resultado.enviados.length} ${resultado.enviados.length === 1 ? 'lugar' : 'lugares'}.`
            : null}
          {resultado.pendientes && resultado.pendientes.length > 0
            ? ' El aviso a toda la iglesia quedó por autorizar: saldrá cuando alguien lo apruebe.'
            : ''}
          {resultado.omitidos.length > 0 ? ` No tenías permiso en ${resultado.omitidos.length}.` : ''}
        </Alert>
      ) : null}

      <Modal
        open={abierto}
        onClose={cerrar}
        title="Enviar un aviso"
        description="Elige a quién llega. Cada persona lo recibe donde participa y, si activó los avisos, en su teléfono."
      >
        <div className="flex flex-col gap-4">
          <TextareaField
            label="Mensaje"
            maxLength={1000}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
          />
          {Object.entries(grupos).map(([titulo, filas]) => (
            <fieldset key={titulo} className="flex flex-col gap-1">
              <legend className="font-bold">{titulo}</legend>
              <div className="flex max-h-48 flex-col gap-1 overflow-y-auto">
                {filas.map((d) => (
                  <div key={clave(d.tipo, d.id)} className="flex flex-wrap items-center gap-2">
                    <CheckboxField
                      label={d.etiqueta}
                      checked={clave(d.tipo, d.id) in elegidos}
                      onChange={(e) =>
                        setElegidos((actual) => {
                          const siguiente = { ...actual }
                          if (e.target.checked) siguiente[clave(d.tipo, d.id)] = { tipo: d.tipo, id: d.id }
                          else delete siguiente[clave(d.tipo, d.id)]
                          return siguiente
                        })
                      }
                    />
                    {d.requiere_autorizacion ? <Badge tone="warning">Requiere autorización</Badge> : null}
                  </div>
                ))}
              </div>
            </fieldset>
          ))}
          {puedePersonas ? (
            <fieldset className="flex flex-col gap-2">
              <legend className="font-bold">Personas</legend>
              <ComboField
                label="Buscar persona"
                options={opciones}
                value=""
                onChange={(id) => {
                  const p = encontradas.data?.results.find((x) => String(x.id) === id)
                  if (p) setPersonas((actual) => ({ ...actual, [p.id]: p.nombre_completo }))
                }}
                onBuscar={setBusqueda}
                filtrar={false}
                limpiarAlElegir
                placeholder="Nombre o número"
                vacio={q.length < 2 ? 'Escribe al menos 2 letras o números.' : 'Nadie coincide con la búsqueda.'}
              />
              {Object.keys(personas).length > 0 ? (
                <ul className="flex flex-wrap gap-2" aria-label="Personas elegidas">
                  {Object.entries(personas).map(([id, nombre]) => (
                    <li key={id}>
                      <Badge tone="primary">
                        {nombre}
                        <button
                          type="button"
                          aria-label={`Quitar a ${nombre}`}
                          className="ml-1 inline-flex"
                          onClick={() =>
                            setPersonas((actual) => {
                              const siguiente = { ...actual }
                              delete siguiente[Number(id)]
                              return siguiente
                            })
                          }
                        >
                          <X aria-hidden className="size-4" />
                        </button>
                      </Badge>
                    </li>
                  ))}
                </ul>
              ) : null}
            </fieldset>
          ) : null}
          {enviar.error ? <Alert tone="destructive">{enviar.error.message}</Alert> : null}
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => enviar.mutate()} disabled={enviar.isPending || total === 0 || !texto.trim()}>
              {total > 0 ? `Enviar a ${total}` : 'Enviar'}
            </Button>
            <Button variant="ghost" onClick={cerrar}>
              Cancelar
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

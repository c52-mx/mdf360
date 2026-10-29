import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Megaphone } from 'lucide-react'
import { useDeferredValue, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  CardDescription,
  CardTitle,
  CheckboxField,
  Field,
  TextareaField,
} from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'

interface Destino {
  tipo: string
  tipo_display: string
  id: number
  etiqueta: string
}
interface PersonaFila {
  id: number
  nombre_completo: string
}
interface Resultado {
  enviados: { tipo: string; id: number; etiqueta: string }[]
  omitidos: { tipo: string; id: number }[]
}

const clave = (tipo: string, id: number) => `${tipo}:${id}`

/** Un mismo aviso para varios lugares: toda la iglesia, grupos, unidades y personas. */
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
    enabled: puedePersonas && q.length >= 2,
    queryFn: () => api<{ results: PersonaFila[] }>(`/api/personas/?q=${encodeURIComponent(q)}&page_size=8`),
  })

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
      setAbierto(false)
      setTexto('')
      setElegidos({})
      setPersonas({})
      void queryClient.invalidateQueries({ queryKey: ['tablero-no-leidos'] })
    },
  })

  // Quien no puede publicar en ningún lugar ni escribir a personas no ve esta tarjeta
  if (!destinos.data || (destinos.data.length === 0 && !puedePersonas)) return null

  const grupos = destinos.data.reduce<Record<string, Destino[]>>((acc, d) => {
    ;(acc[d.tipo_display] ??= []).push(d)
    return acc
  }, {})
  const total = Object.keys(elegidos).length + Object.keys(personas).length

  if (!abierto) {
    return (
      <div>
        <Button onClick={() => setAbierto(true)}>
          <Megaphone aria-hidden className="size-5" />
          Enviar un aviso
        </Button>
        {resultado ? (
          <Alert tone="success" className="mt-3">
            Aviso enviado a {resultado.enviados.length}{' '}
            {resultado.enviados.length === 1 ? 'lugar' : 'lugares'}.
            {resultado.omitidos.length > 0 ? ` No tenías permiso en ${resultado.omitidos.length}.` : ''}
          </Alert>
        ) : null}
      </div>
    )
  }

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <CardTitle>Enviar un aviso</CardTitle>
        <CardDescription>
          Elige a quién llega. Cada persona lo recibe donde participa y, si activó los avisos, en su
          teléfono.
        </CardDescription>
      </div>
      <TextareaField
        label="Mensaje"
        maxLength={1000}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
      />
      {Object.entries(grupos).map(([titulo, filas]) => (
        <fieldset key={titulo} className="flex flex-col gap-1">
          <legend className="font-bold">{titulo}</legend>
          {filas.map((d) => (
            <CheckboxField
              key={clave(d.tipo, d.id)}
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
          ))}
        </fieldset>
      ))}
      {puedePersonas ? (
        <fieldset className="flex flex-col gap-2">
          <legend className="font-bold">Personas</legend>
          <Field
            label="Buscar persona"
            type="search"
            placeholder="Nombre, número o correo"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
          {encontradas.data?.results.map((p) => (
            <CheckboxField
              key={p.id}
              label={p.nombre_completo}
              checked={p.id in personas}
              onChange={(e) =>
                setPersonas((actual) => {
                  const siguiente = { ...actual }
                  if (e.target.checked) siguiente[p.id] = p.nombre_completo
                  else delete siguiente[p.id]
                  return siguiente
                })
              }
            />
          ))}
          {Object.entries(personas)
            .filter(([id]) => !encontradas.data?.results.some((p) => String(p.id) === id))
            .map(([id, nombre]) => (
              <CheckboxField
                key={id}
                label={nombre}
                checked
                onChange={() =>
                  setPersonas((actual) => {
                    const siguiente = { ...actual }
                    delete siguiente[Number(id)]
                    return siguiente
                  })
                }
              />
            ))}
        </fieldset>
      ) : null}
      {enviar.error ? <Alert tone="destructive">{enviar.error.message}</Alert> : null}
      <div className="flex flex-wrap gap-3">
        <Button onClick={() => enviar.mutate()} disabled={enviar.isPending || total === 0 || !texto.trim()}>
          {total > 0 ? `Enviar a ${total}` : 'Enviar'}
        </Button>
        <Button variant="ghost" onClick={() => setAbierto(false)}>
          Cancelar
        </Button>
      </div>
    </Card>
  )
}

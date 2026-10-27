import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert, Badge, Button, Card, CardTitle, TextareaField } from '@/design-system'
import { cn } from '@/lib/cn'

export interface PersonaLista {
  persona_id: number
  nombre: string
  invitado: boolean
  presente: boolean
}

export type ResultadoGuardado = 'enviado' | 'en-cola'

interface Props {
  personas: PersonaLista[]
  notasIniciales: string
  puedeModificar: boolean
  /** Guarda la lista. Devuelve «en-cola» si quedó en el teléfono por falta de conexión. */
  onGuardar: (
    asistencias: { persona_id: number; presente: boolean }[],
    notas: string,
  ) => Promise<ResultadoGuardado>
}

/** Pase de lista: una fila con palomita por persona, contador, notas y guardado (con o sin conexión). */
export function ListaAsistencia({ personas, notasIniciales, puedeModificar, onGuardar }: Props) {
  const [presentes, setPresentes] = useState<Record<number, boolean>>(() =>
    Object.fromEntries(personas.map((p) => [p.persona_id, p.presente])),
  )
  const [notas, setNotas] = useState(notasIniciales)
  const total = Object.values(presentes).filter(Boolean).length

  const guardar = useMutation({
    mutationFn: () =>
      onGuardar(
        Object.entries(presentes).map(([id, presente]) => ({ persona_id: Number(id), presente })),
        notas,
      ),
  })

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <CardTitle>Pasar lista</CardTitle>
        <span className="font-bold text-success">
          {total} de {personas.length} presentes
        </span>
      </div>
      {!puedeModificar ? <Alert tone="warning">Solo puedes consultar esta lista.</Alert> : null}
      <ul className="flex flex-col gap-2">
        {personas.map((p) => {
          const presente = !!presentes[p.persona_id]
          return (
            <li key={p.persona_id}>
              {/* Toda la fila es el área de toque: la palomita refleja el estado */}
              <label
                className={cn(
                  'presionable flex min-h-14 items-center gap-3 rounded-control border-2 px-3 py-2',
                  presente ? 'border-success bg-success-soft' : 'border-border bg-card',
                  puedeModificar ? 'cursor-pointer' : 'opacity-70',
                )}
              >
                <input
                  type="checkbox"
                  checked={presente}
                  disabled={!puedeModificar}
                  onChange={() => setPresentes((m) => ({ ...m, [p.persona_id]: !m[p.persona_id] }))}
                  className="size-7 shrink-0 accent-success"
                />
                <span className="flex-1">
                  <span className="font-bold">{p.nombre}</span>{' '}
                  {p.invitado ? <Badge tone="warning">Invitado</Badge> : null}
                </span>
                <span className={cn('text-sm font-semibold', presente ? 'text-success' : 'text-muted-foreground')}>
                  {presente ? 'Presente' : 'Ausente'}
                </span>
              </label>
            </li>
          )
        })}
      </ul>
      <TextareaField
        label="Notas de la reunión"
        value={notas}
        disabled={!puedeModificar}
        onChange={(ev) => setNotas(ev.target.value)}
      />
      {guardar.data === 'enviado' ? <Alert tone="success">Lista guardada.</Alert> : null}
      {guardar.data === 'en-cola' ? (
        <Alert tone="info">
          Sin conexión: la lista quedó guardada en tu teléfono y se enviará sola cuando haya señal.
        </Alert>
      ) : null}
      {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
      {puedeModificar ? (
        <Button size="lg" onClick={() => guardar.mutate()} disabled={guardar.isPending}>
          {guardar.isPending ? 'Guardando…' : 'Guardar lista'}
        </Button>
      ) : null}
    </Card>
  )
}

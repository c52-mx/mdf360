import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  Field,
  SelectField,
} from '@/design-system'
import { api } from '@/lib/api'

export interface Movimiento {
  tipo: 'captura' | 'correccion' | 'aval'
  monto: string
  diferencia: string | null
  motivo: string
  por: string
  fecha: string
}

export interface Ofrenda {
  id: number
  reunion_id: number
  fecha: string
  grupo: string
  tipo: 'regular' | 'especial'
  tipo_display: string
  concepto: string
  monto: string
  estado: 'pendiente' | 'avalada' | 'diferencia'
  estado_display: string
  con_diferencia: boolean
  movimientos?: Movimiento[]
}

export const dinero = (valor: string | number) =>
  Number(valor).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' })

export const estadoTone = { pendiente: 'warning', avalada: 'success', diferencia: 'destructive' } as const

/** Formulario del Tesorero: cifra contada + PIN. Muestra la diferencia antes de confirmar. */
export function AvalForm({ ofrenda, onListo }: { ofrenda: Ofrenda; onListo: () => void }) {
  const [contado, setContado] = useState('')
  const [pin, setPin] = useState('')
  const diferencia = contado === '' ? null : Number(contado) - Number(ofrenda.monto)

  const avalar = useMutation({
    mutationFn: () =>
      api<Ofrenda>(`/api/grupos/ofrendas/${ofrenda.id}/aval/`, {
        method: 'POST',
        body: { monto_contado: contado, credential: pin },
      }),
    onSuccess: () => {
      setPin('')
      setContado('')
      onListo()
    },
  })
  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    avalar.mutate()
  }

  return (
    <form onSubmit={onSubmit} className="grid max-w-md grid-cols-1 gap-4">
      <Field
        label="Cantidad que contaste"
        inputMode="decimal"
        value={contado}
        onChange={(e) => setContado(e.target.value)}
        required
      />
      {diferencia === null ? null : diferencia === 0 ? (
        <Alert tone="success">La cifra coincide con la capturada.</Alert>
      ) : (
        <Alert tone="warning">
          Hay una diferencia de {dinero(diferencia)} contra lo capturado ({dinero(ofrenda.monto)}). Se
          registrará.
        </Alert>
      )}
      <Field
        label="Escribe tu PIN para avalar"
        type="password"
        autoComplete="current-password"
        hint="Tu aval queda guardado con fecha y hora."
        value={pin}
        onChange={(e) => setPin(e.target.value)}
        required
      />
      {avalar.error ? <Alert tone="destructive">{avalar.error.message}</Alert> : null}
      <Button type="submit" size="lg" disabled={avalar.isPending}>
        {avalar.isPending ? 'Guardando…' : 'Avalar cifra'}
      </Button>
    </form>
  )
}

interface Respuesta {
  ofrendas: Ofrenda[]
  puede_capturar: boolean
  puede_avalar: boolean
}

/** Ofrendas de una reunión: consulta para quien tenga permiso y captura/corrección para el Secretario. */
export function OfrendasReunion({ reunionId }: { reunionId: number }) {
  const queryClient = useQueryClient()
  const clave = ['ofrendas', reunionId]
  const datos = useQuery({
    queryKey: clave,
    queryFn: () => api<Respuesta>(`/api/grupos/reuniones/${reunionId}/ofrendas/`),
    retry: false,
  })
  const [tipo, setTipo] = useState('regular')
  const [concepto, setConcepto] = useState('')
  const [monto, setMonto] = useState('')
  const [corrigiendo, setCorrigiendo] = useState<number | null>(null)
  const [nuevoMonto, setNuevoMonto] = useState('')
  const [motivo, setMotivo] = useState('')
  const refrescar = () => queryClient.invalidateQueries({ queryKey: clave })

  const capturar = useMutation({
    mutationFn: () =>
      api(`/api/grupos/reuniones/${reunionId}/ofrendas/`, {
        method: 'POST',
        body: { tipo, concepto, monto },
      }),
    onSuccess: () => {
      setMonto('')
      setConcepto('')
      void refrescar()
    },
  })
  const corregir = useMutation({
    mutationFn: (id: number) =>
      api(`/api/grupos/ofrendas/${id}/`, { method: 'PATCH', body: { monto: nuevoMonto, motivo } }),
    onSuccess: () => {
      setCorrigiendo(null)
      setNuevoMonto('')
      setMotivo('')
      void refrescar()
    },
  })

  if (datos.isError || !datos.data) return null // sin permiso para ver finanzas de este grupo
  const { ofrendas, puede_capturar: puedeCapturar } = datos.data

  const onCapturar = (e: FormEvent) => {
    e.preventDefault()
    capturar.mutate()
  }

  return (
    <Card className="flex flex-col gap-4">
      <CardTitle>Ofrendas</CardTitle>
      {ofrendas.some((o) => o.estado === 'diferencia') ? (
        <Alert tone="destructive">
          Hay una diferencia entre lo capturado y lo contado por el Tesorero. Verifica la cifra.
        </Alert>
      ) : null}
      {ofrendas.length === 0 ? <CardDescription>Aún no se captura la ofrenda de esta reunión.</CardDescription> : null}
      <ul className="flex flex-col gap-3">
        {ofrendas.map((o) => (
          <li key={o.id} className="flex flex-col gap-2 rounded-control border border-border p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-bold">
                {o.tipo_display}
                {o.concepto ? ` · ${o.concepto}` : ''}
              </span>
              <span className="font-display text-xl font-bold">{dinero(o.monto)}</span>
            </div>
            <Badge tone={estadoTone[o.estado]}>{o.estado_display}</Badge>
            {o.movimientos
              ?.filter((m) => m.tipo === 'aval' || m.tipo === 'correccion')
              .map((m, i) => (
                <CardDescription key={i}>
                  {m.tipo === 'aval'
                    ? `Avalada por ${m.por}: contó ${dinero(m.monto)}${
                        m.diferencia && Number(m.diferencia) !== 0 ? ` (diferencia ${dinero(m.diferencia)})` : ''
                      }`
                    : `Corregida por ${m.por}: ${m.motivo}`}
                </CardDescription>
              ))}
            {puedeCapturar ? (
              corrigiendo === o.id ? (
                <div className="grid max-w-md grid-cols-1 gap-3">
                  <Field label="Monto correcto" inputMode="decimal" value={nuevoMonto} onChange={(e) => setNuevoMonto(e.target.value)} />
                  <Field label="Motivo de la corrección" value={motivo} onChange={(e) => setMotivo(e.target.value)} />
                  {corregir.error ? <Alert tone="destructive">{corregir.error.message}</Alert> : null}
                  <div className="flex gap-3">
                    <Button type="button" onClick={() => corregir.mutate(o.id)} disabled={corregir.isPending}>
                      Guardar corrección
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => setCorrigiendo(null)}>
                      Cancelar
                    </Button>
                  </div>
                </div>
              ) : (
                <div>
                  <Button type="button" size="sm" variant="outline" onClick={() => setCorrigiendo(o.id)}>
                    Corregir
                  </Button>
                </div>
              )
            ) : null}
          </li>
        ))}
      </ul>

      {puedeCapturar ? (
        <form onSubmit={onCapturar} className="grid max-w-md grid-cols-1 gap-4">
          <CardTitle>Capturar ofrenda</CardTitle>
          <SelectField
            label="Tipo"
            value={tipo}
            onChange={(e) => setTipo(e.target.value)}
            options={[
              { value: 'regular', label: 'Ofrenda regular' },
              { value: 'especial', label: 'Ofrenda especial' },
            ]}
          />
          {tipo === 'especial' ? (
            <Field label="Concepto" hint="Ej. Retiro, despensas" value={concepto} onChange={(e) => setConcepto(e.target.value)} required />
          ) : null}
          <Field label="Monto" inputMode="decimal" value={monto} onChange={(e) => setMonto(e.target.value)} required />
          {capturar.error ? <Alert tone="destructive">{capturar.error.message}</Alert> : null}
          <Button type="submit" disabled={capturar.isPending}>
            Guardar ofrenda
          </Button>
          <CardDescription>El Tesorero la contará y la avalará con su PIN.</CardDescription>
        </form>
      ) : null}
    </Card>
  )
}

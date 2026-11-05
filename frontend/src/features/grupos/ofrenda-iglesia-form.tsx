import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Alert, Button, Field, Modal, SelectField } from '@/design-system'
import { api } from '@/lib/api'
import type { TiposRespuesta } from './ofrendas-types'

const hoy = () => new Date().toLocaleDateString('en-CA') // AAAA-MM-DD en hora local

/** Captura de una ofrenda de la iglesia (Secretaria, Pastor y Tesorería); luego pasa por aval. */
export function OfrendaIglesiaForm({ abierto, onCerrar }: { abierto: boolean; onCerrar: () => void }) {
  const queryClient = useQueryClient()
  const [fecha, setFecha] = useState(hoy())
  const [tipo, setTipo] = useState('')
  const [monto, setMonto] = useState('')
  const [nota, setNota] = useState('')
  const tipos = useQuery({
    queryKey: ['ofrendas-tipos', 'iglesia'],
    queryFn: () => api<TiposRespuesta>('/api/grupos/ofrendas/tipos/?para=iglesia'),
    enabled: abierto,
  })
  const activos = (tipos.data?.tipos ?? []).filter((t) => t.activo)

  const capturar = useMutation({
    mutationFn: () =>
      api('/api/grupos/ofrendas/iglesia/', {
        method: 'POST',
        body: { fecha, tipo: Number(tipo), monto, nota },
      }),
    onSuccess: () => {
      setMonto('')
      setNota('')
      onCerrar()
      void queryClient.invalidateQueries({ queryKey: ['ofrendas'] })
      void queryClient.invalidateQueries({ queryKey: ['ofrendas-pendientes'] })
    },
  })
  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    capturar.mutate()
  }

  return (
    <Modal
      open={abierto}
      onClose={onCerrar}
      title="Capturar ofrenda de la iglesia"
      description="Queda pendiente hasta que otra persona cuente y la avale con su PIN."
    >
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field label="Fecha" type="date" max={hoy()} value={fecha} onChange={(e) => setFecha(e.target.value)} required />
        <SelectField
          label="Tipo de ofrenda"
          value={tipo}
          onChange={(e) => setTipo(e.target.value)}
          required
          options={[{ value: '', label: 'Elige un tipo' }, ...activos.map((t) => ({ value: String(t.id), label: t.nombre }))]}
        />
        <Field label="Monto" inputMode="decimal" value={monto} onChange={(e) => setMonto(e.target.value)} required />
        <Field label="Nota (opcional)" maxLength={150} value={nota} onChange={(e) => setNota(e.target.value)} />
        {capturar.error ? <Alert tone="destructive">{capturar.error.message}</Alert> : null}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={capturar.isPending || !tipo || !monto}>
            {capturar.isPending ? 'Guardando…' : 'Capturar'}
          </Button>
          <Button type="button" variant="ghost" onClick={onCerrar}>
            Cancelar
          </Button>
        </div>
      </form>
    </Modal>
  )
}

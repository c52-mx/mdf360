import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  CardDescription,
  CardTitle,
  CheckboxField,
  Field,
  PageHeader,
} from '@/design-system'
import { useCan } from '@/features/auth/use-auth'
import { api } from '@/lib/api'

interface Parametro {
  clave: string
  descripcion: string
  tipo: 'monto' | 'booleano'
  valor: number | boolean
  por_defecto: number | boolean
}

function Fila({ p }: { p: Parametro }) {
  const queryClient = useQueryClient()
  const [valor, setValor] = useState(String(p.valor))
  const guardar = useMutation({
    mutationFn: (nuevo: number | boolean) =>
      api(`/api/config/${p.clave}/`, { method: 'PATCH', body: { valor: nuevo } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] }),
  })

  return (
    <Card className="flex flex-col gap-3">
      <div>
        <CardTitle>{p.descripcion}</CardTitle>
        <CardDescription>
          Valor por defecto: {typeof p.por_defecto === 'boolean' ? (p.por_defecto ? 'Sí' : 'No') : p.por_defecto}
        </CardDescription>
      </div>
      {p.tipo === 'booleano' ? (
        <CheckboxField
          checked={Boolean(p.valor)}
          disabled={guardar.isPending}
          onChange={(e) => guardar.mutate(e.target.checked)}
          label="Activado"
        />
      ) : (
        <div className="flex max-w-md flex-wrap items-end gap-3">
          <Field
            label="Valor"
            inputMode="decimal"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
          />
          <Button onClick={() => guardar.mutate(Number(valor))} disabled={guardar.isPending}>
            Guardar
          </Button>
        </div>
      )}
      {guardar.isSuccess ? <Alert tone="success">Cambio guardado.</Alert> : null}
      {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
    </Card>
  )
}

export function ConfigPage() {
  const puede = useCan('config.gestionar')
  const config = useQuery({
    queryKey: ['config'],
    enabled: puede,
    queryFn: () => api<Parametro[]>('/api/config/'),
  })
  if (!puede) return <Alert tone="warning">No tienes permiso para cambiar la configuración.</Alert>

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Configuración"
        description="Parámetros que se ajustan sin programar. Cada cambio queda en la bitácora."
        module="admin"
      />
      {config.isError ? <Alert tone="destructive">{config.error.message}</Alert> : null}
      {config.data?.map((p) => <Fila key={`${p.clave}-${String(p.valor)}`} p={p} />)}
    </div>
  )
}

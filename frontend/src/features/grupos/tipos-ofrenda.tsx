import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import {
  Alert,
  Badge,
  Button,
  CheckboxField,
  Collapsible,
  DataTable,
  Field,
  Modal,
  type DataColumn,
} from '@/design-system'
import { api } from '@/lib/api'
import type { TipoOfrenda, TiposRespuesta } from './ofrendas-types'

const vacio = { nombre: '', para_grupo: false, para_iglesia: true }

/** Catálogo único de tipos de ofrenda: cada tipo se marca para grupos, para la iglesia o ambos. */
export function TiposOfrenda() {
  const queryClient = useQueryClient()
  const [editando, setEditando] = useState<TipoOfrenda | 'nuevo' | null>(null)
  const [form, setForm] = useState(vacio)
  const tipos = useQuery({
    queryKey: ['ofrendas-tipos', 'todos'],
    queryFn: () => api<TiposRespuesta>('/api/grupos/ofrendas/tipos/'),
  })

  const abrir = (t: TipoOfrenda | 'nuevo') => {
    setForm(t === 'nuevo' ? vacio : { nombre: t.nombre, para_grupo: t.para_grupo, para_iglesia: t.para_iglesia })
    setEditando(t)
  }
  const refrescar = () => {
    void queryClient.invalidateQueries({ queryKey: ['ofrendas-tipos'] })
    void queryClient.invalidateQueries({ queryKey: ['ofrendas'] })
  }
  const guardar = useMutation({
    mutationFn: () =>
      editando === 'nuevo'
        ? api('/api/grupos/ofrendas/tipos/', { method: 'POST', body: form })
        : api(`/api/grupos/ofrendas/tipos/${(editando as TipoOfrenda).id}/`, { method: 'PATCH', body: form }),
    onSuccess: () => {
      setEditando(null)
      refrescar()
    },
  })
  const activar = useMutation({
    mutationFn: (t: TipoOfrenda) =>
      api(`/api/grupos/ofrendas/tipos/${t.id}/`, { method: 'PATCH', body: { activo: !t.activo } }),
    onSuccess: refrescar,
  })

  if (!tipos.data?.puede_administrar) return null

  const columnas: DataColumn<TipoOfrenda>[] = [
    { clave: 'nombre', titulo: 'Tipo', orden: (t) => t.nombre, celda: (t) => <span className="font-bold">{t.nombre}</span> },
    {
      clave: 'donde',
      titulo: 'Se usa en',
      celda: (t) => (
        <span className="flex flex-wrap gap-1">
          {t.para_grupo ? <Badge tone="neutral">Grupos</Badge> : null}
          {t.para_iglesia ? <Badge tone="neutral">Iglesia</Badge> : null}
        </span>
      ),
    },
    {
      clave: 'estado',
      titulo: 'Estado',
      orden: (t) => (t.activo ? 'Activo' : 'Inactivo'),
      celda: (t) => <Badge tone={t.activo ? 'success' : 'warning'}>{t.activo ? 'Activo' : 'Inactivo'}</Badge>,
    },
    {
      clave: 'acciones',
      titulo: 'Acciones',
      celda: (t) => (
        <span className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => abrir(t)}>
            Editar
          </Button>
          <Button size="sm" variant="ghost" disabled={activar.isPending} onClick={() => activar.mutate(t)}>
            {t.activo ? 'Desactivar' : 'Activar'}
          </Button>
        </span>
      ),
    },
  ]

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    guardar.mutate()
  }

  return (
    <Collapsible title="Tipos de ofrenda" summary="Un solo catálogo para los grupos y para la iglesia.">
      <div className="flex flex-col gap-3">
        <div>
          <Button onClick={() => abrir('nuevo')}>Agregar tipo</Button>
        </div>
        {activar.error ? <Alert tone="destructive">{activar.error.message}</Alert> : null}
        <DataTable titulo="Tipos de ofrenda" columnas={columnas} filas={tipos.data.tipos} clave={(t) => t.id} />
      </div>
      <Modal
        open={editando !== null}
        onClose={() => setEditando(null)}
        title={editando === 'nuevo' ? 'Nuevo tipo de ofrenda' : 'Editar tipo de ofrenda'}
        description="Los grupos solo ven los tipos marcados para grupos; la iglesia, los marcados para la iglesia."
      >
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <Field label="Nombre" maxLength={80} value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} required />
          <fieldset className="flex flex-col gap-2">
            <legend className="font-bold">Dónde se usa</legend>
            <CheckboxField label="En los grupos" checked={form.para_grupo} onChange={(e) => setForm({ ...form, para_grupo: e.target.checked })} />
            <CheckboxField label="En la iglesia" checked={form.para_iglesia} onChange={(e) => setForm({ ...form, para_iglesia: e.target.checked })} />
          </fieldset>
          {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={guardar.isPending || !form.nombre.trim()}>
              Guardar
            </Button>
            <Button type="button" variant="ghost" onClick={() => setEditando(null)}>
              Cancelar
            </Button>
          </div>
        </form>
      </Modal>
    </Collapsible>
  )
}

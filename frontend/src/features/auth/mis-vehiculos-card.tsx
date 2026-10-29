import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import {
  Alert,
  Button,
  Card,
  CardDescription,
  CardTitle,
  ConfirmButton,
  Field,
  SelectField,
} from '@/design-system'
import { api } from '@/lib/api'

interface Vehiculo {
  id: number
  tipo: string
  tipo_display: string
  marca: string
  modelo: string
  anio: number | null
  color: string
  placas: string
}

const TIPOS = [
  { value: 'auto', label: 'Auto' },
  { value: 'camioneta', label: 'Camioneta' },
  { value: 'moto', label: 'Motocicleta' },
  { value: 'bicicleta', label: 'Bicicleta' },
  { value: 'otro', label: 'Otro' },
]

const vacio = { tipo: 'auto', marca: '', modelo: '', anio: '', color: '', placas: '' }

/** Bienes ligados a la persona: los vehículos con los que llega a la iglesia. */
export function MisVehiculosCard() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState(vacio)
  const [editando, setEditando] = useState<number | null>(null)

  const lista = useQuery({
    queryKey: ['mis-vehiculos'],
    queryFn: () => api<Vehiculo[]>('/api/personas/mi-perfil/vehiculos/'),
  })
  const refrescar = () => void queryClient.invalidateQueries({ queryKey: ['mis-vehiculos'] })
  const terminar = () => {
    setForm(vacio)
    setEditando(null)
    refrescar()
  }

  const guardar = useMutation({
    mutationFn: () => {
      const body = { ...form, anio: form.anio ? Number(form.anio) : null }
      return editando === null
        ? api('/api/personas/mi-perfil/vehiculos/', { method: 'POST', body })
        : api(`/api/personas/mi-perfil/vehiculos/${editando}/`, { method: 'PATCH', body })
    },
    onSuccess: terminar,
  })
  const quitar = useMutation({
    mutationFn: (id: number) => api(`/api/personas/mi-perfil/vehiculos/${id}/`, { method: 'DELETE' }),
    onSuccess: refrescar,
  })

  const poner = (campo: keyof typeof vacio, valor: string) => setForm({ ...form, [campo]: valor })
  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    guardar.mutate()
  }

  return (
    <Card className="flex flex-col gap-4">
      <CardTitle>Mis vehículos</CardTitle>
      <CardDescription>
        Registra los vehículos con los que llegas a la iglesia. Solo tú los puedes cambiar o quitar.
      </CardDescription>
      {lista.data && lista.data.length === 0 ? <CardDescription>Aún no registras ninguno.</CardDescription> : null}
      <ul className="flex flex-col gap-2">
        {lista.data?.map((v) => (
          <li key={v.id} className="flex flex-wrap items-center justify-between gap-2">
            <span>
              <span className="font-bold">
                {v.tipo_display} {v.marca} {v.modelo}
              </span>
              {v.anio ? ` ${v.anio}` : ''}
              {v.color ? `, ${v.color}` : ''}
              {v.placas ? ` · placas ${v.placas}` : ''}
            </span>
            <span className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                aria-label={`Editar ${v.tipo_display} ${v.marca} ${v.modelo}`.trim()}
                onClick={() => {
                  setEditando(v.id)
                  setForm({
                    tipo: v.tipo,
                    marca: v.marca,
                    modelo: v.modelo,
                    anio: v.anio ? String(v.anio) : '',
                    color: v.color,
                    placas: v.placas,
                  })
                }}
              >
                Editar
              </Button>
              <ConfirmButton
                size="sm"
                variant="outline"
                pregunta="¿Quitar este vehículo?"
                etiquetaConfirmar="Sí, quitar"
                onConfirm={() => quitar.mutate(v.id)}
              >
                Quitar
              </ConfirmButton>
            </span>
          </li>
        ))}
      </ul>
      {quitar.error ? <Alert tone="destructive">{quitar.error.message}</Alert> : null}

      <form onSubmit={onSubmit} className="grid max-w-3xl grid-cols-1 gap-4 md:grid-cols-2">
        <CardTitle>{editando === null ? 'Agregar un vehículo' : 'Editar vehículo'}</CardTitle>
        <span className="hidden md:block" />
        <SelectField label="Tipo" value={form.tipo} onChange={(e) => poner('tipo', e.target.value)} options={TIPOS} />
        <Field label="Marca" value={form.marca} onChange={(e) => poner('marca', e.target.value)} />
        <Field label="Modelo" value={form.modelo} onChange={(e) => poner('modelo', e.target.value)} />
        <Field
          label="Año"
          inputMode="numeric"
          value={form.anio}
          onChange={(e) => poner('anio', e.target.value.replace(/\D/g, '').slice(0, 4))}
        />
        <Field label="Color" value={form.color} onChange={(e) => poner('color', e.target.value)} />
        <Field label="Placas" value={form.placas} onChange={(e) => poner('placas', e.target.value)} />
        <div className="flex flex-col gap-3 md:col-span-2">
          {guardar.error ? <Alert tone="destructive">{guardar.error.message}</Alert> : null}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={guardar.isPending}>
              {editando === null ? 'Agregar vehículo' : 'Guardar cambios'}
            </Button>
            {editando !== null ? (
              <Button type="button" variant="outline" onClick={terminar}>
                Cancelar
              </Button>
            ) : null}
          </div>
        </div>
      </form>
    </Card>
  )
}

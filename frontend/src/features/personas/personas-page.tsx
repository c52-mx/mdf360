import { useQuery } from '@tanstack/react-query'
import { UserPlus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Alert, Avatar, Badge, Button, Card, Field, PageHeader, SelectField } from '@/design-system'
import { api } from '@/lib/api'
import { fotoUrl, nivelLabel, type Nivel, type Pagina, type PersonaResumen } from './types'

const nivelTone: Record<Nivel, 'neutral' | 'primary' | 'success'> = {
  contacto: 'neutral',
  participante: 'primary',
  edu: 'success',
}

export function PersonasPage() {
  const [q, setQ] = useState('')
  const [nivel, setNivel] = useState('')
  const [activo, setActivo] = useState('true')
  const [page, setPage] = useState(1)

  const lista = useQuery({
    queryKey: ['personas', { q, nivel, activo, page }],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), activo })
      if (q.trim()) params.set('q', q.trim())
      if (nivel) params.set('nivel', nivel)
      return api<Pagina<PersonaResumen>>(`/api/personas/?${params.toString()}`)
    },
    placeholderData: (previous) => previous,
  })

  const cambiar = (fn: () => void) => {
    fn()
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Personas"
        description="Expediente digital: contactos, participantes y miembros."
        module="admin"
        actions={
          <Button asChild>
            <Link to="/personas/nueva">
              <UserPlus aria-hidden className="size-5" />
              Nuevo contacto
            </Link>
          </Button>
        }
      />

      <Card className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Field
          label="Buscar"
          type="search"
          placeholder="Nombre, número, correo o grupo"
          value={q}
          onChange={(e) => cambiar(() => setQ(e.target.value))}
        />
        <SelectField
          label="Nivel de registro"
          value={nivel}
          onChange={(e) => cambiar(() => setNivel(e.target.value))}
          options={[
            { value: '', label: 'Todos' },
            { value: 'contacto', label: 'Contacto' },
            { value: 'participante', label: 'Participante' },
            { value: 'edu', label: 'Expediente completo' },
          ]}
        />
        <SelectField
          label="Estado"
          value={activo}
          onChange={(e) => cambiar(() => setActivo(e.target.value))}
          options={[
            { value: 'true', label: 'Activos' },
            { value: 'false', label: 'Dados de baja' },
            { value: 'all', label: 'Todos' },
          ]}
        />
      </Card>

      {lista.isError ? <Alert tone="destructive">{lista.error.message}</Alert> : null}
      {lista.isPending ? <p className="text-muted-foreground">Cargando…</p> : null}

      {lista.data ? (
        <>
          <p className="text-muted-foreground">
            {lista.data.count === 1 ? '1 persona' : `${lista.data.count} personas`}
          </p>
          {lista.data.results.length === 0 ? (
            <Alert>No hay personas con esos filtros.</Alert>
          ) : (
            <ul className="flex flex-col gap-3">
              {lista.data.results.map((p) => (
                <li key={p.id}>
                  <Link to={`/personas/${p.id}`} className="block rounded-card">
                    <Card className="flex items-center gap-4 hover:bg-primary-soft">
                      <Avatar name={p.nombre_completo} src={fotoUrl(p)} />
                      <div className="flex-1">
                        <p className="font-bold">{p.nombre_completo}</p>
                        <p className="text-sm text-muted-foreground">
                          {[p.whatsapp, p.grupo_conexion].filter(Boolean).join(' · ') || 'Sin datos de contacto'}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <Badge tone={nivelTone[p.nivel]}>{nivelLabel[p.nivel]}</Badge>
                        {!p.activo ? <Badge tone="warning">Baja</Badge> : null}
                      </div>
                    </Card>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <div className="flex items-center justify-between">
            <Button variant="outline" disabled={!lista.data.previous} onClick={() => setPage((n) => n - 1)}>
              Anterior
            </Button>
            <span className="text-muted-foreground">Página {page}</span>
            <Button variant="outline" disabled={!lista.data.next} onClick={() => setPage((n) => n + 1)}>
              Siguiente
            </Button>
          </div>
        </>
      ) : null}
    </div>
  )
}

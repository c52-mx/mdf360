import { useQuery } from '@tanstack/react-query'
import { UserPlus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Card,
  Field,
  PageHeader,
  SelectField,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from '@/design-system'
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
  const [grupo, setGrupo] = useState('')
  const [rol, setRol] = useState('')
  const [page, setPage] = useState(1)

  const lista = useQuery({
    queryKey: ['personas', { q, nivel, activo, grupo, rol, page }],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), activo })
      if (q.trim()) params.set('q', q.trim())
      if (nivel) params.set('nivel', nivel)
      if (grupo) params.set('grupo', grupo)
      if (rol) params.set('rol', rol)
      return api<Pagina<PersonaResumen>>(`/api/personas/?${params.toString()}`)
    },
    placeholderData: (previous) => previous,
  })

  const grupos = useQuery({
    queryKey: ['grupos', 'para-filtro'],
    queryFn: () => api<{ id: number; nombre: string }[]>('/api/grupos/'),
    staleTime: 60_000,
  })
  const roles = useQuery({
    queryKey: ['roles-filtro'],
    queryFn: () => api<{ clave: string; nombre: string }[]>('/api/auth/roles/'),
    staleTime: 60_000,
    retry: false,
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
          label="Grupo"
          value={grupo}
          onChange={(e) => cambiar(() => setGrupo(e.target.value))}
          options={[
            { value: '', label: 'Todos' },
            ...(grupos.data ?? []).map((g) => ({ value: String(g.id), label: g.nombre })),
          ]}
        />
        {roles.data ? (
          <SelectField
            label="Rol"
            value={rol}
            onChange={(e) => cambiar(() => setRol(e.target.value))}
            options={[
              { value: '', label: 'Todos' },
              ...roles.data.map((r) => ({ value: r.clave, label: r.nombre })),
            ]}
          />
        ) : null}
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
            <Table aria-label="Personas">
              <TableHead>
                <TableRow className="hover:bg-muted">
                  <TableHeaderCell>Persona</TableHeaderCell>
                  <TableHeaderCell>Contacto</TableHeaderCell>
                  <TableHeaderCell>Grupo</TableHeaderCell>
                  <TableHeaderCell>Roles</TableHeaderCell>
                  <TableHeaderCell>Nivel</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {lista.data.results.map((p) => (
                  <TableRow key={p.id}>
                    <TableCell>
                      <Link to={`/personas/${p.id}`} className="flex items-center gap-3 font-bold underline">
                        <Avatar name={p.nombre_completo} src={fotoUrl(p)} />
                        {p.nombre_completo}
                      </Link>
                    </TableCell>
                    <TableCell>{p.whatsapp || 'Sin datos'}</TableCell>
                    <TableCell>{p.grupos.length > 0 ? p.grupos.join(', ') : p.grupo_conexion || '–'}</TableCell>
                    <TableCell>
                      {p.roles.length > 0 ? (
                        <span className="flex flex-wrap gap-1">
                          {p.roles.map((rol) => (
                            <Badge key={rol}>{rol}</Badge>
                          ))}
                        </span>
                      ) : (
                        '–'
                      )}
                    </TableCell>
                    <TableCell>
                      <span className="flex flex-wrap gap-1">
                        <Badge tone={nivelTone[p.nivel]}>{nivelLabel[p.nivel]}</Badge>
                        {!p.activo ? <Badge tone="warning">Baja</Badge> : null}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
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

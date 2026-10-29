import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Alert, Badge, Button, Card, CardDescription, CardTitle, PageHeader } from '@/design-system'
import { api } from '@/lib/api'
import { EnviarAvisoCard } from './enviar-aviso-card'
import { TableroPanel } from './tablero-panel'

/** Cómo se agrupan los avisos recibidos, en este orden. */
const SECCIONES = [
  { tipo: 'persona', titulo: 'Para ti' },
  { tipo: 'iglesia', titulo: 'Toda la iglesia' },
  { tipo: 'grupo', titulo: 'Mis grupos' },
  { tipo: 'unidad', titulo: 'Mis unidades' },
]

interface Tablero {
  tipo: string
  tipo_display: string
  id: number
  etiqueta: string
  no_leidos: number
  puede_publicar: boolean
}

/** Los tableros de mensajes de todos los lugares donde la persona participa. */
export function AvisosPage() {
  const [abierto, setAbierto] = useState<string | null>(null)
  const tableros = useQuery({
    queryKey: ['tablero-no-leidos', 'mis-tableros'],
    queryFn: () => api<Tablero[]>('/api/tablero/mis-tableros/'),
  })

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Avisos"
        description="Mensajes de la iglesia, de tus grupos y de tus unidades."
        module="grupos"
      />
      <EnviarAvisoCard />
      {tableros.isError ? <Alert tone="destructive">{tableros.error.message}</Alert> : null}
      {SECCIONES.map(({ tipo, titulo }) => {
        const filas = tableros.data?.filter((t) => t.tipo === tipo) ?? []
        if (filas.length === 0) return null
        return (
          <section key={tipo} aria-label={titulo} className="flex flex-col gap-3">
            <h2 className="text-xl">{titulo}</h2>
            <ul className="flex flex-col gap-3">
              {filas.map((t) => {
                const clave = `${t.tipo}:${t.id}`
                const activo = abierto === clave
                return (
                  <li key={clave}>
                    {activo ? (
                      <div className="flex flex-col gap-3">
                        <Button variant="ghost" onClick={() => setAbierto(null)}>
                          Cerrar {t.etiqueta}
                        </Button>
                        <TableroPanel
                          origenTipo={t.tipo}
                          origenId={t.id}
                          puedePublicar={t.puede_publicar}
                          titulo={t.etiqueta}
                        />
                      </div>
                    ) : (
                      <Card className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <CardTitle>{t.etiqueta}</CardTitle>
                          <CardDescription>{t.tipo_display}</CardDescription>
                        </div>
                        <div className="flex items-center gap-3">
                          {t.no_leidos > 0 ? (
                            <Badge tone="destructive">
                              {t.no_leidos === 1 ? '1 mensaje nuevo' : `${t.no_leidos} mensajes nuevos`}
                            </Badge>
                          ) : null}
                          <Button onClick={() => setAbierto(clave)}>Abrir</Button>
                        </div>
                      </Card>
                    )}
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

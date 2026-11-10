import { useInfiniteQuery } from '@tanstack/react-query'
import { Alert, Button, Card, CardDescription, CardTitle } from '@/design-system'
import { api } from '@/lib/api'
import { CLAVE_MURO } from './acciones-publicacion'
import { NuevaPublicacion } from './nueva-publicacion'
import { PublicacionCard } from './publicacion-card'
import type { AudienciaFija, PaginaMuro } from './types'

function urlMuro(antes: number | null, filtro: string): string {
  const params = [antes ? `antes=${antes}` : '', filtro].filter(Boolean).join('&')
  return params ? `/api/muro/?${params}` : '/api/muro/'
}

/** El muro de la persona: lo dirigido a toda la iglesia, a sus segmentos, grupos y ministerios. */
export function MuroFeed({ audiencia }: { audiencia?: AudienciaFija }) {
  const filtro = audiencia ? `audiencia_tipo=${audiencia.tipo}&audiencia_id=${audiencia.id}` : ''
  const muro = useInfiniteQuery({
    queryKey: audiencia ? [...CLAVE_MURO, audiencia.tipo, audiencia.id] : CLAVE_MURO,
    initialPageParam: null as number | null,
    queryFn: ({ pageParam }) => api<PaginaMuro>(urlMuro(pageParam, filtro)),
    getNextPageParam: (ultima) => ultima.siguiente,
  })
  const fijadas = muro.data?.pages[0]?.fijadas ?? []
  const publicaciones = [...fijadas, ...(muro.data?.pages.flatMap((p) => p.resultados) ?? [])]

  if (muro.isError) return <Alert tone="destructive">No se pudo cargar el muro.</Alert>
  const vacio = muro.isSuccess && publicaciones.length === 0
  return (
    <section aria-label="Muro" className="flex flex-col gap-3">
      <NuevaPublicacion audiencia={audiencia} />
      {vacio ? (
        <Card>
          <CardTitle>Tu comunidad</CardTitle>
          <CardDescription>
            {audiencia
              ? 'Aún no hay publicaciones aquí. Lo que se publique para este lugar aparecerá en esta lista.'
              : 'Aún no hay publicaciones para ti. Cuando se publique algo para la iglesia, tus grupos o tus ministerios, lo verás aquí y podrás comentar y reaccionar.'}
          </CardDescription>
        </Card>
      ) : null}
      {publicaciones.map((p) => (
        <PublicacionCard key={p.id} publicacion={p} />
      ))}
      {muro.hasNextPage ? (
        <Button
          variant="ghost"
          onClick={() => void muro.fetchNextPage()}
          disabled={muro.isFetchingNextPage}
        >
          {muro.isFetchingNextPage ? 'Cargando…' : 'Ver más publicaciones'}
        </Button>
      ) : null}
    </section>
  )
}

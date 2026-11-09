import { useInfiniteQuery } from '@tanstack/react-query'
import { Alert, Button, Card, CardDescription, CardTitle } from '@/design-system'
import { api } from '@/lib/api'
import { PublicacionCard, CLAVE_MURO } from './publicacion-card'
import type { PaginaMuro } from './types'

/** El muro de la persona: lo dirigido a toda la iglesia, a sus segmentos, grupos y ministerios. */
export function MuroFeed() {
  const muro = useInfiniteQuery({
    queryKey: CLAVE_MURO,
    initialPageParam: null as number | null,
    queryFn: ({ pageParam }) =>
      api<PaginaMuro>(pageParam ? `/api/muro/?antes=${pageParam}` : '/api/muro/'),
    getNextPageParam: (ultima) => ultima.siguiente,
  })
  const publicaciones = muro.data?.pages.flatMap((p) => p.resultados) ?? []

  if (muro.isError) return <Alert tone="destructive">No se pudo cargar el muro.</Alert>
  if (muro.isSuccess && publicaciones.length === 0) {
    return (
      <Card>
        <CardTitle>Tu comunidad</CardTitle>
        <CardDescription>
          Aún no hay publicaciones para ti. Cuando se publique algo para la iglesia, tus grupos o
          tus ministerios, lo verás aquí y podrás comentar y reaccionar.
        </CardDescription>
      </Card>
    )
  }
  return (
    <section aria-label="Muro" className="flex flex-col gap-3">
      {publicaciones.map((p) => (
        <PublicacionCard key={p.id} publicacion={p} />
      ))}
      {muro.hasNextPage ? (
        <Button variant="ghost" onClick={() => void muro.fetchNextPage()} disabled={muro.isFetchingNextPage}>
          {muro.isFetchingNextPage ? 'Cargando…' : 'Ver más publicaciones'}
        </Button>
      ) : null}
    </section>
  )
}

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { QRCodeSVG } from 'qrcode.react'
import { useState } from 'react'
import { Alert, Badge, Button, Card, CardDescription, CardTitle, ComboField, ConfirmButton, useToast } from '@/design-system'
import { api } from '@/lib/api'

interface Enlace {
  tipo: 'grupo' | 'ministerio'
  id: number
  nombre: string
  /** Ruta del enlace (ej. /unirse/abc) o null si está desactivado. */
  enlace: string | null
  requiere_aprobacion: boolean
}

const clave = (e: Enlace) => `${e.tipo}:${e.id}`
const ruta = (e: Enlace) => `/api/${e.tipo === 'grupo' ? 'grupos' : 'unidades'}/${e.id}/enlace/`

/**
 * El QR fijo de cada grupo y ministerio que la persona gestiona. Se elige con el buscador y se
 * comparte el QR o el enlace. El de un grupo pasa por la aprobación del líder; el de un
 * ministerio suma como servidor sin aprobación.
 */
export function QrEnlacesCard() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const [elegido, setElegido] = useState('')

  const enlaces = useQuery({
    queryKey: ['mis-enlaces'],
    queryFn: () => api<Enlace[]>('/api/grupos/mis-enlaces/'),
  })
  const refrescar = () => queryClient.invalidateQueries({ queryKey: ['mis-enlaces'] })
  const generar = useMutation({
    mutationFn: (e: Enlace) => api(ruta(e), { method: 'POST', body: {} }),
    onSuccess: refrescar,
  })
  const desactivar = useMutation({
    mutationFn: (e: Enlace) => api(ruta(e), { method: 'DELETE' }),
    onSuccess: () => {
      toast.mostrar('El enlace quedó desactivado.')
      void refrescar()
    },
  })

  const lista = enlaces.data ?? []
  // Quien no gestiona a nadie no ve esta sección (ni un destello mientras carga)
  if (enlaces.isError) return <Alert tone="destructive">{enlaces.error.message}</Alert>
  if (!enlaces.isSuccess || lista.length === 0) return null

  const actual = lista.find((e) => clave(e) === elegido)
  const url = actual?.enlace ? `${window.location.origin}${actual.enlace}` : ''
  const error = generar.error ?? desactivar.error ?? enlaces.error

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <CardTitle>Invitar con un QR</CardTitle>
        <CardDescription>
          Cada grupo y cada ministerio tiene su QR fijo. Elige uno y compártelo: la persona deja su nombre y
          WhatsApp. En un grupo espera tu aprobación; en un ministerio entra de inmediato como servidor.
        </CardDescription>
      </div>
      {error ? <Alert tone="destructive">{error.message}</Alert> : null}
      <ComboField
        label="Grupo o ministerio"
        options={lista.map((e) => ({
          value: clave(e),
          label: e.nombre,
          detalle: e.tipo === 'grupo' ? 'Grupo de Conexión' : 'Ministerio',
        }))}
        value={elegido}
        onChange={setElegido}
        placeholder="Escribe el nombre"
        vacio="No hay grupos ni ministerios con ese nombre."
      />
      {actual ? (
        actual.enlace ? (
          <div className="flex flex-wrap items-start gap-6">
            <div className="rounded-card bg-card p-3 ring-1 ring-border">
              <QRCodeSVG value={url} size={160} role="img" aria-label={`Código QR de ${actual.nombre}`} />
            </div>
            <div className="flex min-w-0 flex-1 flex-col gap-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-bold">{actual.nombre}</span>
                <Badge tone={actual.requiere_aprobacion ? 'warning' : 'success'}>
                  {actual.requiere_aprobacion ? 'Con aprobación del líder' : 'Entra sin aprobación'}
                </Badge>
              </div>
              <p className="break-all font-semibold">{url}</p>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() => {
                    void navigator.clipboard.writeText(url)
                    toast.mostrar('Enlace copiado.')
                  }}
                >
                  Copiar enlace
                </Button>
                <ConfirmButton
                  size="sm"
                  variant="outline"
                  pregunta="El enlace y el QR anteriores dejarán de servir. ¿Generar uno nuevo?"
                  etiquetaConfirmar="Sí, generar"
                  onConfirm={() => generar.mutate(actual)}
                >
                  Generar uno nuevo
                </ConfirmButton>
                <ConfirmButton
                  size="sm"
                  variant="outline"
                  pregunta="¿Desactivar el enlace?"
                  etiquetaConfirmar="Sí, desactivar"
                  onConfirm={() => desactivar.mutate(actual)}
                >
                  Desactivar
                </ConfirmButton>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-start gap-2">
            <CardDescription>El enlace de {actual.nombre} está desactivado.</CardDescription>
            <Button onClick={() => generar.mutate(actual)} disabled={generar.isPending}>
              Crear enlace y QR
            </Button>
          </div>
        )
      ) : null}
    </Card>
  )
}

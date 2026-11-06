import { useMutation, useQueryClient } from '@tanstack/react-query'
import { QRCodeSVG } from 'qrcode.react'
import { Alert, Button, Card, CardDescription, CardTitle, ConfirmButton, useToast } from '@/design-system'
import { api } from '@/lib/api'

/** QR fijo del ministerio: quien lo escanea se suma como servidor, sin esperar aprobación. */
export function EnlaceUnidadCard({ unidadId, nombre, enlace }: { unidadId: number; nombre: string; enlace: string | null }) {
  const queryClient = useQueryClient()
  const toast = useToast()
  const refrescar = () => {
    void queryClient.invalidateQueries({ queryKey: ['unidad', String(unidadId)] })
    void queryClient.invalidateQueries({ queryKey: ['mis-enlaces'] })
  }
  const ruta = `/api/unidades/${unidadId}/enlace/`
  const generar = useMutation({ mutationFn: () => api(ruta, { method: 'POST', body: {} }), onSuccess: refrescar })
  const desactivar = useMutation({
    mutationFn: () => api(ruta, { method: 'DELETE' }),
    onSuccess: () => {
      toast.mostrar('El enlace quedó desactivado.')
      refrescar()
    },
  })
  const url = enlace ? `${window.location.origin}${enlace}` : ''
  const error = generar.error ?? desactivar.error

  return (
    <Card className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <CardTitle>Invitar con QR</CardTitle>
        <CardDescription>
          Quien escanee este QR deja su nombre y WhatsApp y entra al ministerio de inmediato como servidor.
          Los roles con más alcance los asigna quien administra el ministerio.
        </CardDescription>
      </div>
      {error ? <Alert tone="destructive">{error.message}</Alert> : null}
      {enlace ? (
        <div className="flex flex-wrap items-start gap-6">
          <div className="rounded-card bg-card p-3 ring-1 ring-border">
            <QRCodeSVG value={url} size={160} role="img" aria-label={`Código QR de ${nombre}`} />
          </div>
          <div className="flex min-w-0 flex-1 flex-col gap-3">
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
                onConfirm={() => generar.mutate()}
              >
                Generar uno nuevo
              </ConfirmButton>
              <ConfirmButton
                size="sm"
                variant="outline"
                pregunta="¿Desactivar el enlace?"
                etiquetaConfirmar="Sí, desactivar"
                onConfirm={() => desactivar.mutate()}
              >
                Desactivar
              </ConfirmButton>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-start gap-2">
          <CardDescription>El enlace está desactivado.</CardDescription>
          <Button onClick={() => generar.mutate()} disabled={generar.isPending}>
            Crear enlace y QR
          </Button>
        </div>
      )}
    </Card>
  )
}

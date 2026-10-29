import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button } from '@/design-system'
import { api } from '@/lib/api'

interface PerfilAviso {
  aviso_pendiente: boolean
}

/** Cuando cambia el aviso de privacidad, cada persona lo lee y lo acepta de nuevo. */
export function AvisoPendiente() {
  const queryClient = useQueryClient()
  const perfil = useQuery({
    queryKey: ['mi-perfil'],
    queryFn: () => api<PerfilAviso>('/api/personas/mi-perfil/'),
    staleTime: 60_000,
  })
  const aviso = useQuery({
    queryKey: ['aviso-privacidad'],
    enabled: perfil.data?.aviso_pendiente === true,
    queryFn: () => api<{ version: string; texto: string }>('/api/personas/aviso-privacidad/'),
  })
  const aceptar = useMutation({
    mutationFn: () => api('/api/personas/mi-perfil/aceptar-aviso/', { method: 'POST', body: {} }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['mi-perfil'] }),
  })

  if (!perfil.data?.aviso_pendiente || !aviso.data) return null
  return (
    <Alert tone="warning">
      <div className="flex flex-col gap-3">
        <span className="font-bold">Actualizamos el aviso de privacidad. Léelo y acéptalo para continuar.</span>
        <details>
          <summary className="cursor-pointer font-semibold">Leer el aviso (versión {aviso.data.version})</summary>
          <p className="mt-2 whitespace-pre-line">{aviso.data.texto}</p>
        </details>
        {aceptar.error ? <span>{aceptar.error.message}</span> : null}
        <div>
          <Button onClick={() => aceptar.mutate()} disabled={aceptar.isPending}>
            Acepto el aviso de privacidad
          </Button>
        </div>
      </div>
    </Alert>
  )
}

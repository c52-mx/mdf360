import { Bell, BellRing } from 'lucide-react'
import { Alert, Button, Card, CardDescription, CardTitle } from '@/design-system'
import { usePush, type EstadoPush } from './use-push'

const EXPLICACION: Partial<Record<EstadoPush, string>> = {
  instalar:
    'En iPhone y iPad los avisos solo funcionan con la aplicación instalada: abre este sitio en Safari, toca Compartir y elige «Agregar a pantalla de inicio». Luego ábrela desde ese ícono.',
  'no-soportado': 'Este navegador no puede recibir avisos. Prueba con Chrome o Safari actualizados.',
  apagado: 'Los avisos no están activos en este momento.',
  bloqueado:
    'Bloqueaste los avisos para este sitio. Para recibirlos, permítelos en los ajustes del navegador (candado junto a la dirección) y vuelve aquí.',
}

/** Activar o apagar los avisos en este dispositivo (M1-09). */
export function NotificacionesCard() {
  const { estado, ocupado, error, activar, desactivar, probar } = usePush()

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        {estado === 'activo' ? (
          <BellRing className="size-5 text-primary" aria-hidden />
        ) : (
          <Bell className="size-5 text-muted-foreground" aria-hidden />
        )}
        <CardTitle>Avisos en este teléfono</CardTitle>
      </div>
      <CardDescription>
        Recibe una notificación con sonido y vibración cuando haya un mensaje nuevo en tus grupos o
        llegue el estudio de la semana. El sonido y la vibración dependen de los ajustes de tu
        teléfono.
      </CardDescription>
      {EXPLICACION[estado] ? <Alert tone="info">{EXPLICACION[estado]}</Alert> : null}
      {error ? <Alert tone="destructive">{error}</Alert> : null}
      {estado === 'inactivo' ? (
        <div>
          <Button onClick={() => void activar()} disabled={ocupado}>
            Activar avisos
          </Button>
        </div>
      ) : null}
      {estado === 'activo' ? (
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void probar()}>
            Enviarme una prueba
          </Button>
          <Button variant="ghost" onClick={() => void desactivar()} disabled={ocupado}>
            Desactivar
          </Button>
        </div>
      ) : null}
    </Card>
  )
}

/** Invitación breve en la pantalla de inicio; desaparece al activar o si no se puede activar. */
export function InvitacionAvisos() {
  const { estado, ocupado, activar } = usePush()
  if (estado !== 'inactivo' && estado !== 'instalar') return null
  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Bell className="size-5 text-primary" aria-hidden />
        <CardTitle>No te pierdas los avisos</CardTitle>
      </div>
      <CardDescription>
        {estado === 'instalar'
          ? 'Instala la aplicación en tu pantalla de inicio para recibir avisos con sonido y vibración. Los pasos están en «Mi cuenta».'
          : 'Activa las notificaciones para enterarte al momento de los mensajes de tu grupo y del estudio de la semana.'}
      </CardDescription>
      {estado === 'inactivo' ? (
        <div>
          <Button onClick={() => void activar()} disabled={ocupado}>
            Activar avisos
          </Button>
        </div>
      ) : null}
    </Card>
  )
}

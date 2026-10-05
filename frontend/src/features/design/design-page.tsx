import { Badge, Button, Card, CardDescription, CardTitle, Field, PageHeader } from '@/design-system'

/** Catálogo vivo del sistema de diseño: así se ve cada componente. Ruta: /diseno */
export function DesignPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Sistema de diseño"
        description="Componentes globales. Si necesitas algo nuevo, agrégalo aquí, no en la pantalla."
        module="admin"
      />

      <Card className="flex flex-col gap-3">
        <CardTitle>Botones</CardTitle>
        <div className="flex flex-wrap gap-3">
          <Button>Guardar lista</Button>
          <Button variant="outline">Ver estudio</Button>
          <Button variant="success">Presente</Button>
          <Button variant="destructive">Eliminar</Button>
          <Button variant="ghost">Cancelar</Button>
          <Button size="lg">Avalar cifra</Button>
        </div>
      </Card>

      <Card className="flex flex-col gap-3">
        <CardTitle>Estados</CardTitle>
        <div className="flex flex-wrap gap-3">
          <Badge>Pendiente</Badge>
          <Badge tone="primary">En diseño</Badge>
          <Badge tone="success">Ofrenda avalada</Badge>
          <Badge tone="warning">Pendiente de aval</Badge>
          <Badge tone="destructive">Diferencia</Badge>
        </div>
      </Card>

      <Card className="flex flex-col gap-4">
        <CardTitle>Campos</CardTitle>
        <Field label="Número de WhatsApp" hint="10 dígitos, sin espacios" placeholder="5512345678" />
        <Field label="PIN" type="password" error="El PIN debe tener 6 dígitos" />
      </Card>

      <Card>
        <CardTitle>Reglas</CardTitle>
        <CardDescription>
          Las pantallas usan estos componentes y no definen colores, tamaños ni estilos propios.
          Se valida automáticamente con npm run lint:styles.
        </CardDescription>
      </Card>
    </div>
  )
}

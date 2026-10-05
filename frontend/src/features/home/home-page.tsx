import { Card, CardDescription, CardTitle, PageHeader } from '@/design-system'

export function HomePage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Bienvenido a MDF360"
        description="Plataforma de gestión y discipulado de Mundo de Fe México."
        module="admin"
      />
      <Card>
        <CardTitle>Sprint 0</CardTitle>
        <CardDescription>
          Base del proyecto lista. Siguiente paso: acceso con WhatsApp y PIN.
        </CardDescription>
      </Card>
    </div>
  )
}

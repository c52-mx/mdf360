import { Alert, CardDescription, CardLink, CardTitle, PageHeader } from '@/design-system'
import { useCan } from '@/features/auth/use-auth'

const FORMULARIOS = [
  {
    to: '/formularios/persona',
    titulo: 'Personas',
    texto: 'Datos que se piden en el expediente y en el alta de una persona.',
  },
  {
    to: '/formularios/grupo',
    titulo: 'Grupos de Conexión',
    texto: 'Datos adicionales de cada grupo.',
  },
  {
    to: '/peticiones/formulario',
    titulo: 'Peticiones de oración',
    texto: 'Lo que se captura al registrar una petición.',
  },
]

/** Los formularios que la iglesia puede adaptar sin programar. */
export function FormulariosPage() {
  const puede = useCan('formularios.gestionar')
  if (!puede) return <Alert tone="warning">No tienes permiso para diseñar formularios.</Alert>
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Formularios"
        description="Agrega, ordena y desactiva campos sin programar. Los campos no se borran: se desactivan."
        module="admin"
      />
      <ul className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {FORMULARIOS.map((f) => (
          <li key={f.to}>
            <CardLink to={f.to} className="flex h-full flex-col gap-1">
              <CardTitle>{f.titulo}</CardTitle>
              <CardDescription>{f.texto}</CardDescription>
            </CardLink>
          </li>
        ))}
      </ul>
    </div>
  )
}

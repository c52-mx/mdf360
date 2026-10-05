/** Módulos de la plataforma. Cada uno tiene un color de marca definido en theme.css. */
export type ModuleKey = 'grupos' | 'cursos' | 'kids' | 'admin'

export const moduleBg: Record<ModuleKey, string> = {
  grupos: 'bg-module-grupos',
  cursos: 'bg-module-cursos',
  kids: 'bg-module-kids',
  admin: 'bg-module-admin',
}

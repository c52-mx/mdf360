import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Une clases de Tailwind resolviendo conflictos. Solo para uso dentro de src/design-system. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

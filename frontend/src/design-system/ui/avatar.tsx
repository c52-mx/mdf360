import { useState } from 'react'
import { cn } from '@/lib/cn'

interface AvatarProps {
  name: string
  src?: string
  size?: 'md' | 'lg'
}

/** Foto de la persona; si no hay foto (o no carga) muestra sus iniciales. */
export function Avatar({ name, src, size = 'md' }: AvatarProps) {
  const [failed, setFailed] = useState(false)
  const initials = name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')
  const box = cn('shrink-0 rounded-full', size === 'lg' ? 'size-24' : 'size-12')
  if (src && !failed) {
    return <img src={src} alt={name} onError={() => setFailed(true)} className={cn(box, 'object-cover')} />
  }
  return (
    <span
      aria-label={name}
      className={cn(
        box,
        'flex items-center justify-center bg-primary-soft font-bold text-primary',
        size === 'lg' ? 'text-2xl' : 'text-base',
      )}
    >
      {initials}
    </span>
  )
}

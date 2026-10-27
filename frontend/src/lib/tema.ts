/** Paletas de color que cada persona puede elegir. Los valores viven en styles/theme.css. */
export const TEMAS = [
  { clave: 'morado', nombre: 'Morado' },
  { clave: 'azul', nombre: 'Azul' },
  { clave: 'verde', nombre: 'Verde' },
  { clave: 'vino', nombre: 'Vino' },
  { clave: 'grafito', nombre: 'Grafito' },
] as const

export type TemaClave = (typeof TEMAS)[number]['clave']

const CLAVE = 'mdf360.tema'

export function temaGuardado(): TemaClave {
  try {
    const guardado = localStorage.getItem(CLAVE)
    return TEMAS.some((t) => t.clave === guardado) ? (guardado as TemaClave) : 'morado'
  } catch {
    return 'morado'
  }
}

/** Aplica la paleta a toda la aplicación; «morado» es la de origen y no lleva atributo. */
export function aplicarTema(clave: TemaClave, recordar = true) {
  const raiz = document.documentElement
  if (clave === 'morado') raiz.removeAttribute('data-tema')
  else raiz.setAttribute('data-tema', clave)
  if (!recordar) return
  try {
    localStorage.setItem(CLAVE, clave)
  } catch {
    // sin almacenamiento: el tema se aplica, pero no se recuerda en la próxima visita
  }
}

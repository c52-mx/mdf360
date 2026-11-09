import { describe, expect, it } from 'vitest'
import { espacioDeRuta, espaciosDe } from './espacios'

describe('espacios', () => {
  it('quien no administra nada solo tiene Comunidad y Grupos', () => {
    expect(espaciosDe([])).toEqual(['comunidad', 'grupos'])
    // Líder y Supervisor: registrar contactos e invitar es servicio, no administración
    expect(espaciosDe(['personas.crear', 'usuarios.invitar'])).toEqual(['comunidad', 'grupos'])
  })

  it('con un permiso administrativo aparece Administración', () => {
    expect(espaciosDe(['personas.ver'])).toContain('admin')
    expect(espaciosDe(['config.gestionar'])).toContain('admin')
    expect(espaciosDe(undefined)).toEqual(['comunidad', 'grupos'])
  })

  it('ubica cada ruta en su espacio', () => {
    const sin = espaciosDe([])
    const con = espaciosDe(['personas.ver'])
    expect(espacioDeRuta('/', sin)).toBe('comunidad')
    expect(espacioDeRuta('/cuenta', sin)).toBe('comunidad')
    expect(espacioDeRuta('/peticiones/formulario', sin)).toBe('comunidad')
    expect(espacioDeRuta('/grupos/3', sin)).toBe('grupos')
    expect(espacioDeRuta('/peticiones', sin)).toBe('grupos')
    expect(espacioDeRuta('/roles', con)).toBe('admin')
    expect(espacioDeRuta('/personas/7', con)).toBe('admin')
  })

  it('las rutas de uso mixto siguen a la persona', () => {
    expect(espacioDeRuta('/ofrendas', espaciosDe([]))).toBe('grupos')
    expect(espacioDeRuta('/ofrendas', espaciosDe(['personas.ver']))).toBe('admin')
    expect(espacioDeRuta('/personas/nueva', espaciosDe([]))).toBe('grupos')
    expect(espacioDeRuta('/invitar', espaciosDe(['config.gestionar']))).toBe('admin')
  })
})

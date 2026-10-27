import { afterEach, describe, expect, it, vi } from 'vitest'
import { claveABytes, quitarDispositivo, requiereInstalar, soportaPush, TOPE_BAJA_MS } from './push'

afterEach(() => vi.unstubAllGlobals())

describe('claveABytes', () => {
  it('convierte la clave pública VAPID (base64 URL) a bytes', () => {
    // 0xfb 0xff 0xbe en base64 estándar es «+/++»; en base64 URL, «-_--»
    expect(Array.from(claveABytes('-_--'))).toEqual([0xfb, 0xff, 0xbe])
  })

  it('acepta claves sin relleno', () => {
    expect(Array.from(claveABytes('AQID'))).toEqual([1, 2, 3])
    expect(Array.from(claveABytes('AQI'))).toEqual([1, 2])
  })
})

describe('soportaPush', () => {
  it('es falso donde no hay service worker (p. ej. este entorno de pruebas)', () => {
    expect(soportaPush()).toBe(false)
  })
})

describe('requiereInstalar', () => {
  const ua = (valor: string) =>
    vi.spyOn(window.navigator, 'userAgent', 'get').mockReturnValue(valor)

  it('en iPhone desde Safari hay que instalar la aplicación', () => {
    ua('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit Safari')
    window.matchMedia = vi.fn().mockReturnValue({ matches: false }) as never
    expect(requiereInstalar()).toBe(true)
  })

  it('en iPhone con la aplicación instalada ya no', () => {
    ua('Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit Safari')
    window.matchMedia = vi.fn().mockReturnValue({ matches: true }) as never
    expect(requiereInstalar()).toBe(false)
  })

  it('en Android nunca', () => {
    ua('Mozilla/5.0 (Linux; Android 14; SM-S918B) Chrome/130')
    window.matchMedia = vi.fn().mockReturnValue({ matches: false }) as never
    expect(requiereInstalar()).toBe(false)
  })
})

describe('quitarDispositivo', () => {
  it('no estorba al cerrar sesión cuando no hay soporte', async () => {
    await expect(quitarDispositivo()).resolves.toBeUndefined()
  })

  it('si el service worker nunca responde, cierra de todos modos pasado el tope', async () => {
    vi.useFakeTimers()
    Object.defineProperty(navigator, 'serviceWorker', {
      configurable: true,
      value: { ready: new Promise(() => {}) },
    })
    vi.stubGlobal('PushManager', class {})
    vi.stubGlobal('Notification', class {})
    try {
      let terminado = false
      const espera = quitarDispositivo().then(() => {
        terminado = true
      })
      await vi.advanceTimersByTimeAsync(TOPE_BAJA_MS - 100)
      expect(terminado).toBe(false)
      await vi.advanceTimersByTimeAsync(200)
      await espera
      expect(terminado).toBe(true)
    } finally {
      vi.useRealTimers()
      Reflect.deleteProperty(navigator, 'serviceWorker')
    }
  })
})

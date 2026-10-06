export class ApiError extends Error {
  status: number
  code?: string
  constructor(message: string, status: number, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

function readCookie(name: string): string | null {
  const match = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.split('=')[1]) : null
}

async function csrfToken(): Promise<string> {
  const existing = readCookie('csrftoken')
  if (existing) return existing
  const res = await fetch('/api/auth/csrf/', { credentials: 'same-origin' })
  return ((await res.json()) as { csrfToken: string }).csrfToken
}

interface Options {
  method?: 'GET' | 'POST'
  body?: unknown
}

/** Cliente de la API. Envía la cookie de sesión y el token CSRF en las peticiones que modifican datos. */
export async function api<T>(path: string, { method = 'GET', body }: Options = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (method !== 'GET') {
    headers['Content-Type'] = 'application/json'
    headers['X-CSRFToken'] = await csrfToken()
  }
  const res = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: 'same-origin',
  })
  if (res.status === 204) return undefined as T
  const data = (await res.json().catch(() => ({}))) as { detail?: string; code?: string }
  if (!res.ok) {
    throw new ApiError(data.detail ?? 'Ocurrió un error. Intenta de nuevo.', res.status, data.code)
  }
  return data as T
}

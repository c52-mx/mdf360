import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LoginPage } from './login-page'
import { AuthProvider } from './use-auth'

function respond(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }))
}

function setup(fetchImpl: (url: string) => Promise<Response>) {
  vi.stubGlobal('fetch', vi.fn(fetchImpl))
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('LoginPage', () => {
  it('muestra los campos para entrar y la ayuda de primera vez', async () => {
    setup((url) => (url.includes('/me/') ? respond(403, {}) : respond(200, { csrfToken: 'x' })))
    expect(await screen.findByLabelText('WhatsApp o correo')).toBeInTheDocument()
    expect(screen.getByLabelText('PIN o contraseña')).toBeInTheDocument()
    expect(screen.getByText(/primera vez/i)).toBeInTheDocument()
  })

  it('muestra el mensaje del servidor cuando el PIN es incorrecto', async () => {
    setup((url) => {
      if (url.includes('/me/')) return respond(403, {})
      if (url.includes('/csrf/')) return respond(200, { csrfToken: 'x' })
      return respond(400, { code: 'invalid', detail: 'Número, correo o PIN incorrectos.' })
    })
    fireEvent.change(await screen.findByLabelText('WhatsApp o correo'), {
      target: { value: '5511112222' },
    })
    fireEvent.change(screen.getByLabelText('PIN o contraseña'), { target: { value: '000001' } })
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('Número, correo o PIN incorrectos.'),
    )
  })
})

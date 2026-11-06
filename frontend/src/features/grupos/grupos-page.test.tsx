import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { GruposPage } from './grupos-page'

vi.mock('@/features/auth/use-auth', () => ({ useCan: () => false }))

const json = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }))

const grupo = (id: number, nombre: string, extra = {}) => ({
  id, nombre, tipo: 'conexion', sector: 'K', casa: id, ubicacion: `Sector K, Casa ${id}`, suspendido: false,
  suspension_motivo: '', suspendido_en: null, colonia: 'Centro', dia_semana: 1, dia: 'Martes', hora: '19:30',
  lideres: ['Laura'], integrantes: id * 3, mis_roles: [], ofrendas_con_diferencia: null, ...extra,
})

function montar() {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) =>
      url.includes('/csrf/') ? json({ csrfToken: 'x' }) : json([grupo(2, 'Norte'), grupo(1, 'Sur', { suspendido: true }), grupo(3, 'Centro')]),
    ),
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <GruposPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const nombres = () =>
  within(screen.getByRole('region', { name: 'Grupos' }))
    .getAllByRole('link')
    .map((l) => l.textContent)

afterEach(() => vi.unstubAllGlobals())

describe('GruposPage', () => {
  it('muestra los grupos en una tabla ordenada por nombre y enlaza a cada uno', async () => {
    montar()
    await screen.findByRole('link', { name: 'Norte' })
    expect(nombres()).toEqual(['Centro', 'Norte', 'Sur'])
    expect(screen.getByRole('link', { name: 'Norte' })).toHaveAttribute('href', '/grupos/2')
    expect(screen.getByText('Suspendido')).toBeInTheDocument()
  })

  it('se ordena por integrantes al tocar el título de la columna', async () => {
    montar()
    await screen.findByRole('link', { name: 'Norte' })
    const boton = screen.getByRole('button', { name: /Integrantes/ })
    fireEvent.click(boton)
    expect(nombres()).toEqual(['Sur', 'Norte', 'Centro']) // 3, 6, 9
    fireEvent.click(boton)
    expect(nombres()).toEqual(['Centro', 'Norte', 'Sur'])
  })
})

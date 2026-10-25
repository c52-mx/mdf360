import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './features/auth/use-auth'
import './styles/theme.css'

// networkMode «always»: con el navegador sin red, la petición se intenta igual para que el
// service worker responda desde su caché y las escrituras puedan quedar en la cola local.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      networkMode: 'always',
      retry: (intentos, error) => !(error instanceof TypeError) && intentos < 1,
    },
    mutations: { networkMode: 'always' },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
)

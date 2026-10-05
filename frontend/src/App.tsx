import { Home, Palette } from 'lucide-react'
import { Route, Routes } from 'react-router-dom'
import { AppShell, type NavItem } from '@/design-system'
import { DesignPage } from '@/features/design/design-page'
import { HomePage } from '@/features/home/home-page'

const nav: NavItem[] = [
  { to: '/', label: 'Inicio', icon: Home },
  { to: '/diseno', label: 'Diseño', icon: Palette, module: 'admin' },
]

export default function App() {
  return (
    <AppShell nav={nav}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/diseno" element={<DesignPage />} />
      </Routes>
    </AppShell>
  )
}

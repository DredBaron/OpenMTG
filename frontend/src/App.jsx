import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'
import Login from './pages/Login'
import Setup from './pages/Setup'
import Collection from './pages/Collection'
import Decks from './pages/Decks'
import DeckDetail from './pages/DeckDetail'
import Scanner from './pages/Scanner'
import Stats from './pages/Stats'
import Admin from './pages/Admin'
import Layout from './components/Layout'
import Settings from './pages/Settings'

function PrivateRoute({ children }) {
  const { user, loading, setupRequired } = useAuth()
  if (loading) return <div className="loading">Loading…</div>
  if (setupRequired) return <Navigate to="/setup" replace />
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  const { setupRequired, loading } = useAuth()

  if (loading) return <div className="loading">Loading…</div>

  if (setupRequired) {
    return (
      <Routes>
        <Route path="/setup" element={<Setup />} />
        <Route path="*" element={<Navigate to="/setup" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route path="/setup" element={<Navigate to="/" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<PrivateRoute><Layout /></PrivateRoute>}>
        <Route index element={<Navigate to="/collection" />} />
        <Route path="collection" element={<Collection />} />
        <Route path="decks" element={<Decks />} />
        <Route path="decks/:id" element={<DeckDetail />} />
        <Route path="scanner" element={<Scanner />} />
        <Route path="stats" element={<Stats />} />
        <Route path="admin" element={<Admin />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

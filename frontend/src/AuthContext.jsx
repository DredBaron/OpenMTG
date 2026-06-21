import { createContext, useState, useEffect } from 'react'
import api from './api'

export const AuthContext = createContext(null) // eslint-disable-line react-refresh/only-export-components

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [setupRequired, setSetupRequired] = useState(false)
  const [showroomEnabled, setShowroomEnabled] = useState(true)
  const [scannerEnabled, setScannerEnabled] = useState(true)

  useEffect(() => {
    const init = async () => {
      try {
        const setup = await api.get('/auth/setup-required')
        if (setup.data.setup_required) {
          setSetupRequired(true)
          setLoading(false)
          return
        }
      } catch {
        setLoading(false)
      }

      try {
        const feat = await api.get('/showroom/status')
        setShowroomEnabled(feat.data.enabled)
      } catch { /* non-fatal */ }

      try {
        const feat = await api.get('/scanner/status')
        setScannerEnabled(feat.data.enabled)
      } catch { /* non-fatal */ }

      const token = localStorage.getItem('token')
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const me = await api.get('/auth/me')
        setUser(me.data)
      } catch {
        localStorage.removeItem('token')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const login = async (username, password) => {
    const form = new FormData()
    form.append('username', username)
    form.append('password', password)
    const res = await api.post('/auth/login', form)
    localStorage.setItem('token', res.data.access_token)
    const me = await api.get('/auth/me')
    setUser(me.data)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
    window.location.href = '/login'
  }

  const completeSetup = () => {
    setSetupRequired(false)
  }

  const refreshUser = async () => {
    try {
      const me = await api.get('/auth/me')
      setUser(me.data)
    } catch { /* refreshUser failing is non-fatal */ }
  }

  return (
    <AuthContext.Provider value={{ user, loading, setupRequired, showroomEnabled, scannerEnabled, login, logout, completeSetup, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}


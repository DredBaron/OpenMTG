import { createContext, useState, useEffect } from 'react'
import api from './api'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [setupRequired, setSetupRequired] = useState(false)

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

  return (
    <AuthContext.Provider value={{ user, loading, setupRequired, login, logout, completeSetup }}>
      {children}
    </AuthContext.Provider>
  )
}


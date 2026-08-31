import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import api from '../api'

export default function Setup() {

  useEffect(() => { document.title = 'Setup - OpenMTG' }, [])

  const navigate = useNavigate()
  const { completeSetup, dbBackend } = useAuth()
  const [form, setForm] = useState({ username: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (form.password !== form.confirm) {
      setError('Passwords do not match')
      return
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    setLoading(true)
    try {
      await api.post('/auth/setup', {
        username: form.username,
        email: form.email,
        password: form.password,
      })
      completeSetup()
      navigate('/login')
    } catch (err) {
      setError(err.response?.data?.detail || 'Setup failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>OpenMTG</h1>
        <p>Welcome! Create your admin account to get started.</p>
        <div className="setup-info-banner">
          This is a one-time setup. After this, only admins can create new accounts.
          {dbBackend && (
            <> This instance is running on <strong>{dbBackend === 'sqlite' ? 'SQLite' : 'PostgreSQL'}</strong> - this can't be changed after setup.</>
          )}
        </div>
        {error && <div className="error">{error}</div>}
        <form onSubmit={submit}>
          <div className="form-group">
            <label>Admin Username</label>
            <input autoFocus value={form.username}
              onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={form.email}
              onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" value={form.password}
              onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
          </div>
          <div className="form-group">
            <label>Confirm Password</label>
            <input type="password" value={form.confirm}
              onChange={e => setForm(f => ({ ...f, confirm: e.target.value }))} />
          </div>
          <button className="btn btn-primary btn-block"
            type="submit"
            disabled={loading || !form.username || !form.email || !form.password}>
            {loading ? 'Creating Admin Account' : 'Create Admin Account'}
          </button>
        </form>
      </div>
    </div>
  )
}

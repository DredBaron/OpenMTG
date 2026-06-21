import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, ShieldCheck, ShieldOff, KeyRound, X, Pencil, Check } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useIsMobile } from '../hooks/useIsMobile'
import { useCurrency } from '../hooks/useCurrency'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import ConfirmModal from '../components/ConfirmModal'

function CreateUserModal({ onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({ username: '', email: '', password: '', is_admin: false })
  const [error, setError] = useState('')

  const create = useMutation({
    mutationFn: () => api.post('/admin/users', form),
    onSuccess: () => { qc.invalidateQueries(['admin-users']); onClose() },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to create user'),
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Create User</h2>
        {error && <div className="error">{error}</div>}
        <div className="form-group">
          <label>Username</label>
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
          <label className="checkbox-label">
            <input type="checkbox" checked={form.is_admin}
              onChange={e => setForm(f => ({ ...f, is_admin: e.target.checked }))}
              style={{ width: 'auto' }} />
            Grant admin privileges
          </label>
        </div>
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => create.mutate()}
            disabled={!form.username || !form.email || !form.password || create.isPending}>
            {create.isPending ? 'Creating' : 'Create User'}
          </button>
        </div>
      </div>
    </div>
  )
}

function ResetPasswordModal({ user, onClose }) {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')

  const reset = useMutation({
    mutationFn: () => api.patch(`/admin/users/${user.id}`, { password }),
    onSuccess: onClose,
    onError: (err) => setError(err.response?.data?.detail || 'Failed to reset password'),
  })

  const submit = () => {
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    reset.mutate()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Reset Password: {user.username}</h2>
        {error && <div className="error">{error}</div>}
        <div className="form-group">
          <label>New Password</label>
          <input type="password" autoFocus value={password}
            onChange={e => setPassword(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Confirm Password</label>
          <input type="password" value={confirm}
            onChange={e => setConfirm(e.target.value)} />
        </div>
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={submit} disabled={reset.isPending}>
            {reset.isPending ? 'Resetting' : 'Reset Password'}
          </button>
        </div>
      </div>
    </div>
  )
}

function CurrencyManager() {
  const qc = useQueryClient()
  const [code, setCode] = useState('')
  const [symbol, setSymbol] = useState('')
  const [error, setError] = useState('')
  const [editingCode, setEditingCode] = useState(null)
  const [editSymbol, setEditSymbol] = useState('')

  const { data: currencies = [], isLoading } = useQuery({
    queryKey: ['admin-currencies'],
    queryFn: () => api.get('/admin/currencies').then(r => r.data),
  })

  const add = useMutation({
    mutationFn: () => api.post('/admin/currencies', { code, symbol }),
    onSuccess: () => {
      qc.invalidateQueries(['admin-currencies'])
      qc.invalidateQueries(['currencies'])
      setCode('')
      setSymbol('')
      setError('')
    },
    onError: (err) => setError(err.response?.data?.detail || 'Failed to add currency'),
  })

  const remove = useMutation({
    mutationFn: (c) => api.delete(`/admin/currencies/${c}`),
    onSuccess: () => {
      qc.invalidateQueries(['admin-currencies'])
      qc.invalidateQueries(['currencies'])
    },
  })

  const updateSymbol = useMutation({
    mutationFn: ({ c, sym }) => api.patch(`/admin/currencies/${c}`, { symbol: sym }),
    onSuccess: () => {
      qc.invalidateQueries(['admin-currencies'])
      qc.invalidateQueries(['currencies'])
      setEditingCode(null)
    },
  })

  return (
    <div className="currency-section">
      <div className="page-header" style={{ marginBottom: '1rem' }}>
        <h2 className="currency-heading">Converted Currencies</h2>
      </div>

      <div className="currency-add-row">
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label style={{ fontSize: '0.8rem' }}>Code (3 letters)</label>
          <input
            value={code}
            onChange={e => { setCode(e.target.value.toUpperCase()); setError('') }}
            placeholder="GBP"
            maxLength={3}
            className="currency-code-input"
          />
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label style={{ fontSize: '0.8rem' }}>Symbol</label>
          <input
            value={symbol}
            onChange={e => setSymbol(e.target.value)}
            placeholder="£"
            maxLength={5}
            style={{ width: '5rem' }}
          />
        </div>
        <button
          className="btn btn-primary btn-sm"
          onClick={() => add.mutate()}
          disabled={code.length !== 3 || !symbol || add.isPending}
        >
          {add.isPending ? '...' : <><Plus size={14} /> Add</>}
        </button>
      </div>

      {error && <div className="error" style={{ marginBottom: '0.75rem' }}>{error}</div>}

      {isLoading && <div className="loading">Loading</div>}

      {!isLoading && currencies.length === 0 && (
        <div className="currencies-empty">
          No converted currencies configured. Add one above.
        </div>
      )}

      {currencies.length > 0 && (
        <table className="table" style={{ maxWidth: 480 }}>
          <thead>
            <tr>
              <th>Code</th>
              <th>Symbol</th>
              <th>Rate (from USD)</th>
              <th>Updated</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {currencies.map(c => (
              <tr key={c.code}>
                <td style={{ fontWeight: 600 }}>{c.code}</td>
                <td>
                  {editingCode === c.code ? (
                    <div className="currency-symbol-cell">
                      <input
                        autoFocus
                        value={editSymbol}
                        onChange={e => setEditSymbol(e.target.value)}
                        maxLength={5}
                        className="currency-input-edit"
                        onKeyDown={e => {
                          if (e.key === 'Enter') updateSymbol.mutate({ c: c.code, sym: editSymbol })
                          if (e.key === 'Escape') setEditingCode(null)
                        }}
                      />
                      <button
                        className="btn btn-ghost btn-sm"
                        style={{ color: 'var(--success)' }}
                        onClick={() => updateSymbol.mutate({ c: c.code, sym: editSymbol })}
                        disabled={!editSymbol || updateSymbol.isPending}
                      >
                        <Check size={14} />
                      </button>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => setEditingCode(null)}
                      >
                        <X size={14} />
                      </button>
                    </div>
                  ) : (
                    <div className="currency-symbol-cell">
                      {c.symbol}
                      <button
                        className="btn btn-ghost btn-sm"
                        style={{ opacity: 0.5 }}
                        onClick={() => { setEditingCode(c.code); setEditSymbol(c.symbol) }}
                      >
                        <Pencil size={12} />
                      </button>
                    </div>
                  )}
                </td>
                <td className="currency-rate-cell">
                  {c.rate != null ? c.rate.toFixed(4) : '-'}
                </td>
                <td className="text-muted-sm">
                  {c.rate_updated_at ? new Date(c.rate_updated_at).toLocaleDateString() : '-'}
                </td>
                <td>
                  <button
                    className="btn btn-ghost btn-sm"
                    style={{ color: 'var(--danger)' }}
                    onClick={() => remove.mutate(c.code)}
                    disabled={remove.isPending}
                  >
                    <X size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function Admin() {

  useEffect(() => { document.title = 'User Management - OpenMTG' }, [])

  const { user, refreshUser } = useAuth()
  const { markets } = useCurrency()
  const isMobile = useIsMobile()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [resettingUser, setResettingUser] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null)

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.get('/admin/users').then(r => r.data),
    enabled: !!user?.is_admin,
  })

  const setCurrency = useMutation({
    mutationFn: ({ id, preferred_currency }) =>
      api.patch(`/admin/users/${id}`, { preferred_currency }),
    onSuccess: async () => {
      await refreshUser()
      qc.invalidateQueries(['admin-users'])
      qc.invalidateQueries(['collection'])
      qc.invalidateQueries(['stats'])
      qc.invalidateQueries(['wishlist'])
      qc.invalidateQueries(['decks'])
    },
  })

  const toggleAdmin = useMutation({
    mutationFn: ({ id, is_admin }) => api.patch(`/admin/users/${id}`, { is_admin }),
    onSuccess: () => qc.invalidateQueries(['admin-users']),
  })

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }) => api.patch(`/admin/users/${id}`, { is_active }),
    onSuccess: () => qc.invalidateQueries(['admin-users']),
  })

  const deleteUser = useMutation({
    mutationFn: (id) => api.delete(`/admin/users/${id}`),
    onSuccess: () => qc.invalidateQueries(['admin-users']),
  })

  if (user && !user.is_admin) {
    navigate('/')
    return null
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>User Management</h1>
          <div className="page-subtitle">
            {users.length} account{users.length !== 1 ? 's' : ''}
          </div>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
          <Plus size={18} /> Create User
        </button>
      </div>

      {isLoading && <div className="loading">Loading users</div>}

      {isMobile ? (
        <div className="admin-user-list">
          {users.map(u => (
            <div key={u.id} className="admin-user-card">
              <div className="admin-user-card-info">
                <span className="admin-user-card-name">{u.username}</span>
                {u.id === user.id && <span className="user-self-label">You</span>}
                {u.is_admin
                  ? <span className="badge badge-admin">Admin</span>
                  : <span className="badge badge-user">User</span>}
                {u.is_active
                  ? <span className="badge badge-nm">Active</span>
                  : <span className="badge badge-mp">Disabled</span>}
              </div>
              <div className="admin-user-card-actions">
                <select
                  value={u.preferred_currency}
                  onChange={e => setCurrency.mutate({ id: u.id, preferred_currency: e.target.value })}
                  className="currency-select"
                >
                  {Object.entries(markets || {}).map(([code, m]) => (
                    <option key={code} value={code}>{m.display}</option>
                  ))}
                </select>
                {u.id !== user.id && (
                  <>
                    <button className="btn btn-ghost btn-sm"
                      title={u.is_admin ? 'Remove admin' : 'Make admin'}
                      onClick={() => toggleAdmin.mutate({ id: u.id, is_admin: !u.is_admin })}>
                      {u.is_admin ? <ShieldOff size={14} /> : <ShieldCheck size={14} />}
                    </button>
                    <button className="btn btn-ghost btn-sm"
                      title="Reset password"
                      onClick={() => setResettingUser(u)}>
                      <KeyRound size={14} />
                    </button>
                    <button className="btn btn-ghost btn-sm"
                      title={u.is_active ? 'Disable account' : 'Enable account'}
                      onClick={() => toggleActive.mutate({ id: u.id, is_active: !u.is_active })}
                      style={{ color: u.is_active ? 'var(--danger)' : 'var(--success)' }}>
                      {u.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button className="btn btn-danger btn-sm"
                      onClick={() => setConfirmAction({
                        message: `Delete ${u.username}?`,
                        onConfirm: () => { deleteUser.mutate(u.id); setConfirmAction(null) }
                      })}>
                      <Trash2 size={14} />
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Created</th>
              <th>Currency</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td>
                  <div style={{ fontWeight: 600 }}>{u.username}</div>
                  {u.id === user.id &&
                    <div className="user-self-label">You</div>}
                </td>
                <td className="user-cell-muted">{u.email}</td>
                <td>
                  {u.is_admin
                    ? <span className="badge badge-admin">Admin</span>
                    : <span className="badge badge-user">User</span>}
                </td>
                <td>
                  {u.is_active
                    ? <span className="badge badge-nm">Active</span>
                    : <span className="badge badge-mp">Disabled</span>}
                </td>
                <td className="text-muted-sm">
                  {new Date(u.created_at).toLocaleDateString()}
                </td>
                <td>
                  <select
                    value={u.preferred_currency}
                    onChange={e => setCurrency.mutate({ id: u.id, preferred_currency: e.target.value })}
                    className="currency-select"
                  >
                    {Object.entries(markets || {}).map(([code, m]) => (
                      <option key={code} value={code}>{m.display}</option>
                    ))}
                  </select>
                </td>
                <td>
                  {u.id !== user.id && (
                    <div className="flex-gap">
                      <button className="btn btn-ghost btn-sm"
                        title={u.is_admin ? 'Remove admin' : 'Make admin'}
                        onClick={() => toggleAdmin.mutate({ id: u.id, is_admin: !u.is_admin })}>
                        {u.is_admin ? <ShieldOff size={14} /> : <ShieldCheck size={14} />}
                      </button>
                      <button className="btn btn-ghost btn-sm"
                        title="Reset password"
                        onClick={() => setResettingUser(u)}>
                        <KeyRound size={14} />
                      </button>
                      <button className="btn btn-ghost btn-sm"
                        title={u.is_active ? 'Disable account' : 'Enable account'}
                        onClick={() => toggleActive.mutate({ id: u.id, is_active: !u.is_active })}
                        style={{ color: u.is_active ? 'var(--danger)' : 'var(--success)' }}>
                        {u.is_active ? 'Disable' : 'Enable'}
                      </button>
                      <button className="btn btn-danger btn-sm"
                        onClick={() => setConfirmAction({
                          message: `Delete ${u.username}?`,
                          onConfirm: () => { deleteUser.mutate(u.id); setConfirmAction(null) }
                        })}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <CurrencyManager />

      {showCreate && <CreateUserModal onClose={() => setShowCreate(false)} />}
      {resettingUser && <ResetPasswordModal user={resettingUser} onClose={() => setResettingUser(null)} />}
      {confirmAction && (
        <ConfirmModal
          message={confirmAction.message}
          onConfirm={confirmAction.onConfirm}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>
  )
}

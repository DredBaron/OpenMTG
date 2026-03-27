import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, ShieldCheck, ShieldOff, KeyRound } from 'lucide-react'
import { useAuth } from '../AuthContext'
import { useNavigate } from 'react-router-dom'
import api from '../api'

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
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
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
            {create.isPending ? 'Creating…' : 'Create User'}
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
            {reset.isPending ? 'Resetting…' : 'Reset Password'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Admin() {

  useEffect(() => { document.title = 'User Management - OpenMTG' }, [])

  const { user } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [resettingUser, setResettingUser] = useState(null)

  if (user && !user.is_admin) {
    navigate('/')
    return null
  }

  const { data: users = [], isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.get('/admin/users').then(r => r.data),
    enabled: !!user?.is_admin,
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

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>User Management</h1>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            {users.length} account{users.length !== 1 ? 's' : ''}
          </div>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={18} /> Create User
        </button>
      </div>

      {isLoading && <div className="isLoading">Loading users…</div>}

      <table className="table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Created</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users.map(u => (
            <tr key={u.id}>
              <td>
                <div style={{ fontWeight: 600 }}>{u.username}</div>
                {u.id === user.id &&
                  <div style={{ fontSize: '0.75rem', color: 'var(--accent)' }}>You</div>}
              </td>
              <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{u.email}</td>
              <td>
                {u.is_admin
                  ? <span className="badge" style={{ background: 'var(--foil-bg)', color: 'var(--foil)' }}>
                      Admin
                    </span>
                  : <span className="badge" style={{ background: 'var(--surface2)',
                      color: 'var(--text-muted)' }}>
                      User
                    </span>}
              </td>
              <td>
                {u.is_active
                  ? <span className="badge badge-nm">Active</span>
                  : <span className="badge badge-mp">Disabled</span>}
              </td>
              <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {new Date(u.created_at).toLocaleDateString()}
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
                      onClick={() => confirm(`Delete ${u.username}?`) && deleteUser.mutate(u.id)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showCreate && <CreateUserModal onClose={() => setShowCreate(false)} />}
      {resettingUser && <ResetPasswordModal user={resettingUser} onClose={() => setResettingUser(null)} />}
    </div>
  )
}

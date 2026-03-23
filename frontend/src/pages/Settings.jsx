import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../AuthContext'
import { useNavigate } from 'react-router-dom'
import { RefreshCw, Save, Clock, Zap, Database } from 'lucide-react'
import api from '../api'

export default function Settings() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()

  if (user && !user.is_admin) {
    navigate('/')
    return null
  }

  const { data: currentSettings, isLoading: loadingSettings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get('/admin/settings').then(r => r.data),
    enabled: !!user?.is_admin,
  })

  const { data: status, isLoading: loadingStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['refresh-status'],
    queryFn: () => api.get('/admin/settings/refresh-status').then(r => r.data),
    enabled: !!user?.is_admin,
    refetchInterval: 30000,  // poll every 30s
  })

  const [form, setForm] = useState({
    price_refresh_hours: 72,
    scryfall_rps: 1,
  })
  const [refreshing, setRefreshing] = useState(false)
  const [refreshMsg, setRefreshMsg] = useState('')

  useEffect(() => {
    if (currentSettings) {
      setForm({
        price_refresh_hours: parseInt(currentSettings.price_refresh_hours),
        scryfall_rps: parseInt(currentSettings.scryfall_rps),
      })
    }
  }, [currentSettings])

  const save = useMutation({
    mutationFn: () => api.patch('/admin/settings', form),
    onSuccess: () => qc.invalidateQueries(['settings']),
  })

  const triggerRefresh = async () => {
    setRefreshing(true)
    setRefreshMsg('')
    try {
      const res = await api.post('/admin/settings/refresh-now')
      setRefreshMsg(res.data.message)
      setTimeout(() => refetchStatus(), 3000)
    } catch (err) {
      setRefreshMsg(err.response?.data?.detail || 'Failed to start refresh')
    } finally {
      setRefreshing(false)
    }
  }

  const hoursToHuman = (h) => {
    if (h < 24) return `${h} hour${h !== 1 ? 's' : ''}`
    const days = Math.floor(h / 24)
    const rem = h % 24
    return rem > 0 ? `${days}d ${rem}h` : `${days} day${days !== 1 ? 's' : ''}`
  }

  const formatDate = (iso) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleString()
  }

  const stalePct = status
    ? Math.round((status.stale_cards / (status.total_cards || 1)) * 100)
    : 0

  return (
    <div style={{ maxWidth: 720 }}>
      <div className="page-header">
        <h1>Settings</h1>
      </div>

      {/* Cache Status Card */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius)', padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-muted)',
          textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem',
          display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Database size={15} /> Card Price Cache
        </div>

        {loadingStatus
          ? <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Loading…</div>
          : status && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '1rem', marginBottom: '1rem' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>
                    {status.total_cards}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Cached Cards
                  </div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.75rem', fontWeight: 700,
                    color: status.fresh_cards > 0 ? 'var(--success)' : 'var(--text-muted)' }}>
                    {status.fresh_cards}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Fresh
                  </div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '1.75rem', fontWeight: 700,
                    color: status.stale_cards > 0 ? 'var(--gold)' : 'var(--text-muted)' }}>
                    {status.stale_cards}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Stale
                  </div>
                </div>
              </div>

              {/* Freshness bar */}
              {status.total_cards > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between',
                    fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.3rem' }}>
                    <span>Cache freshness</span>
                    <span>{100 - stalePct}% fresh</span>
                  </div>
                  <div style={{ background: 'var(--surface2)', borderRadius: 4,
                    height: 8, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', borderRadius: 4,
                      width: `${100 - stalePct}%`,
                      background: stalePct > 50 ? 'var(--danger)'
                        : stalePct > 20 ? 'var(--gold)'
                        : 'var(--success)',
                      transition: 'width 0.6s ease',
                    }} />
                  </div>
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr',
                gap: '0.5rem', fontSize: '0.8rem',
                color: 'var(--text-muted)', marginBottom: '1rem' }}>
                <div>Oldest: <span style={{ color: 'var(--text)' }}>
                  {formatDate(status.oldest_fetch)}
                </span></div>
                <div>Newest: <span style={{ color: 'var(--text)' }}>
                  {formatDate(status.newest_fetch)}
                </span></div>
              </div>

              {refreshMsg && (
                <div style={{ background: '#1a2a3a', border: '1px solid #4a90d9',
                  borderRadius: 'var(--radius)', padding: '0.6rem 0.75rem',
                  fontSize: '0.85rem', color: '#4a90d9', marginBottom: '0.75rem' }}>
                  {refreshMsg}
                </div>
              )}

              <button className="btn btn-ghost" onClick={triggerRefresh}
                disabled={refreshing || status.total_cards === 0}>
                <RefreshCw size={16} style={{
                  animation: refreshing ? 'spin 1s linear infinite' : 'none'
                }} />
                {refreshing ? 'Starting Refresh…' : 'Refresh Prices Now'}
              </button>
            </>
          )}
      </div>

      {/* Settings Form */}
      <div style={{ background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius)', padding: '1.25rem', marginBottom: '1.5rem' }}>
        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-muted)',
          textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1.25rem' }}>
          Price Refresh Settings
        </div>

        {loadingSettings
          ? <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Loading…</div>
          : (
            <>
              {/* Refresh interval */}
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Clock size={14} /> Auto-refresh Interval
                </label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <input
                    type="range"
                    min={1} max={168} step={1}
                    value={form.price_refresh_hours}
                    onChange={e => setForm(f => ({
                      ...f, price_refresh_hours: parseInt(e.target.value)
                    }))}
                    style={{ flex: 1, accentColor: 'var(--accent)' }}
                  />
                  <div style={{ minWidth: 80, textAlign: 'right',
                    fontWeight: 600, color: 'var(--accent)' }}>
                    {hoursToHuman(form.price_refresh_hours)}
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between',
                  fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  <span>1 hour</span>
                  <span>Default: 3 days</span>
                  <span>7 days</span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                  Prices older than {hoursToHuman(form.price_refresh_hours)} will be
                  automatically refreshed. The scheduler checks every 30 minutes.
                </div>
              </div>

              {/* RPS setting */}
              <div className="form-group" style={{ marginTop: '1.25rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Zap size={14} /> Scryfall API Rate Limit
                </label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <input
                    type="range"
                    min={1} max={10} step={1}
                    value={form.scryfall_rps}
                    onChange={e => setForm(f => ({
                      ...f, scryfall_rps: parseInt(e.target.value)
                    }))}
                    style={{ flex: 1, accentColor: 'var(--accent)' }}
                  />
                  <div style={{ minWidth: 80, textAlign: 'right',
                    fontWeight: 600, color: 'var(--accent)' }}>
                    {form.scryfall_rps} req/s
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between',
                  fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  <span>1/s (safe)</span>
                  <span>10/s (max)</span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
                  Scryfall's guidelines recommend no more than 10 requests per second.
                  Staying at 1/s is safest and avoids any risk of being rate limited.
                </div>
              </div>

              <div style={{ marginTop: '1.5rem' }}>
                <button className="btn btn-primary" onClick={() => save.mutate()}
                  disabled={save.isPending}>
                  <Save size={16} />
                  {save.isPending ? 'Saving…' : 'Save Settings'}
                </button>
                {save.isSuccess && (
                  <span style={{ marginLeft: '0.75rem', fontSize: '0.875rem',
                    color: 'var(--success)' }}>
                    ✓ Saved
                  </span>
                )}
              </div>
            </>
          )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}

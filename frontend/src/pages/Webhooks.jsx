import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, RefreshCw, Send, Copy, Check, X, ShieldOff, ShieldCheck } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useIsMobile } from '../hooks/useIsMobile'
import api from '../api'
import ConfirmModal from '../components/ConfirmModal'

function NewCredentialModal({ onClose, onCreated }) {
  const [label, setLabel] = useState('')
  const [targetUrl, setTargetUrl] = useState('')
  const [skipVerify, setSkipVerify] = useState(false)
  const [error, setError] = useState('')

  const create = useMutation({
    mutationFn: () => api.post('/webhooks', {
      label: label.trim(),
      target_url: targetUrl.trim() || null,
      verify_tls: !skipVerify,
    }),
    onSuccess: (res) => onCreated(res.data),
    onError: (err) => setError(err.response?.data?.detail || 'Failed to create credential'),
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>New Webhook Credential</h2>
        {error && <div className="error">{error}</div>}
        <div className="form-group">
          <label>Label</label>
          <input autoFocus value={label} onChange={e => setLabel(e.target.value)} placeholder="Living Room HA" />
        </div>
        <div className="form-group">
          <label>Home Assistant Webhook URL (optional)</label>
          <input value={targetUrl} onChange={e => setTargetUrl(e.target.value)}
            placeholder="https://homeassistant.local:8123/api/webhook/xxxx" />
          <div className="field-hint">
            Trade and wishlist alerts push here. Leave blank for a pull-only credential used just to
            fetch stats.
          </div>
        </div>
        <div className="form-group">
          <label className="checkbox-label">
            <input type="checkbox" checked={skipVerify}
              onChange={e => setSkipVerify(e.target.checked)}
              style={{ width: 'auto' }} />
            Skip TLS certificate verification
          </label>
          <div className="field-hint">
            Only enable this for a target URL with a self-signed certificate or an internal CA on
            your own trusted network (e.g. Home Assistant reachable at https://homeassistant.local). Leave off
            for any URL with a normal publicly-trusted certificate.
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => create.mutate()}
            disabled={!label.trim() || create.isPending}>
            {create.isPending ? 'Creating' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}

function SecretRevealModal({ credential, onClose }) {
  const [copiedField, setCopiedField] = useState(null)
  const fullUrl = `${window.location.origin}${credential.inbound_url}`

  const copy = async (field, text) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedField(field)
      setTimeout(() => setCopiedField(f => (f === field ? null : f)), 1500)
    } catch { /* clipboard unavailable */ }
  }

  return (
    <div className="modal-overlay">
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Webhook Credential Created</h2>
        <div className="info-banner" style={{ marginBottom: '1rem' }}>
          The secret below is shown once and cannot be retrieved again. Save it in Home Assistant now.
        </div>
        <div className="form-group">
          <label>Inbound Stats URL</label>
          <div className="secret-row">
            <code className="secret-value">{fullUrl}</code>
            <button className="btn btn-ghost btn-sm" onClick={() => copy('url', fullUrl)}>
              {copiedField === 'url' ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </div>
          <div className="field-hint">
            Configure a Home Assistant RESTful sensor against this URL with header
            <code> Authorization: Bearer &lt;secret&gt;</code>.
          </div>
        </div>
        <div className="form-group">
          <label>Bearer Secret</label>
          <div className="secret-row">
            <code className="secret-value">{credential.secret}</code>
            <button className="btn btn-ghost btn-sm" onClick={() => copy('secret', credential.secret)}>
              {copiedField === 'secret' ? <Check size={14} /> : <Copy size={14} />}
            </button>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-primary" onClick={onClose}>Done, I've saved it</button>
        </div>
      </div>
    </div>
  )
}

function CredentialActions({ credential, onToggle, onToggleVerify, onRegenerate, onTest, onDelete, testMessage }) {
  return (
    <>
      <div className="flex-gap">
        {credential.target_url && (
          <>
            <button className="btn btn-ghost btn-sm" title="Send test event" onClick={onTest}>
              <Send size={14} />
            </button>
            <button className="btn btn-ghost btn-sm"
              title={credential.verify_tls ? 'TLS verification on, click to skip for a self-signed/internal cert' : 'TLS verification skipped (insecure), click to require a valid certificate'}
              onClick={onToggleVerify}
              style={{ color: credential.verify_tls ? undefined : 'var(--gold)' }}>
              {credential.verify_tls ? <ShieldCheck size={14} /> : <ShieldOff size={14} />}
            </button>
          </>
        )}
        <button className="btn btn-ghost btn-sm"
          title={credential.enabled ? 'Disable' : 'Enable'}
          onClick={onToggle}
          style={{ color: credential.enabled ? 'var(--danger)' : 'var(--success)' }}>
          {credential.enabled ? <X size={14} /> : <Check size={14} />}
        </button>
        <button className="btn btn-ghost btn-sm" title="Regenerate secret" onClick={onRegenerate}>
          <RefreshCw size={14} />
        </button>
        <button className="btn btn-danger btn-sm" title="Delete" onClick={onDelete}>
          <Trash2 size={14} />
        </button>
      </div>
      {testMessage && <div className="text-muted-sm">{testMessage}</div>}
    </>
  )
}

export default function Webhooks() {
  useEffect(() => { document.title = 'Webhooks - OpenMTG' }, [])

  const { homeAssistantEnabled } = useAuth()
  const isMobile = useIsMobile()
  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [revealCredential, setRevealCredential] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null)
  const [testMessages, setTestMessages] = useState({})

  const { data: credentials = [], isLoading } = useQuery({
    queryKey: ['webhook-credentials'],
    queryFn: () => api.get('/webhooks').then(r => r.data),
    enabled: homeAssistantEnabled,
  })

  const invalidate = () => qc.invalidateQueries(['webhook-credentials'])

  const toggleEnabled = useMutation({
    mutationFn: ({ id, enabled }) => api.patch(`/webhooks/${id}`, { enabled }),
    onSuccess: invalidate,
  })

  const toggleVerifyTls = useMutation({
    mutationFn: ({ id, verify_tls }) => api.patch(`/webhooks/${id}`, { verify_tls }),
    onSuccess: invalidate,
  })

  const deleteCredential = useMutation({
    mutationFn: (id) => api.delete(`/webhooks/${id}`),
    onSuccess: invalidate,
  })

  const regenerate = useMutation({
    mutationFn: (id) => api.post(`/webhooks/${id}/regenerate-secret`),
    onSuccess: (res) => { invalidate(); setRevealCredential(res.data) },
  })

  const testPush = useMutation({
    mutationFn: (id) => api.post(`/webhooks/${id}/test`),
    onSuccess: (_res, id) => setTestMessages(m => ({ ...m, [id]: 'Sent!' })),
    onError: (err, id) => setTestMessages(m => ({ ...m, [id]: err.response?.data?.detail || 'Failed to send' })),
  })

  const confirmDelete = (c) => setConfirmAction({
    message: `Delete "${c.label}"? Any Home Assistant automation using it will stop receiving events.`,
    onConfirm: () => { deleteCredential.mutate(c.id); setConfirmAction(null) },
  })

  if (!homeAssistantEnabled) {
    return (
      <div className="empty-state">
        <p>Home Assistant integration is currently disabled.</p>
        <p>Ask an admin to enable it from Settings.</p>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Webhooks</h1>
          <div className="page-subtitle">
            {credentials.length} credential{credentials.length !== 1 ? 's' : ''}
          </div>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
          <Plus size={18} /> New Credential
        </button>
      </div>

      {isLoading && <div className="loading">Loading</div>}

      {!isLoading && credentials.length === 0 && (
        <div className="empty-state">
          <p>No webhook credentials yet.</p>
          <p>Create one to push trade and wishlist alerts to Home Assistant, or pull live collection stats.</p>
        </div>
      )}

      {credentials.length > 0 && (isMobile ? (
        <div className="webhook-list">
          {credentials.map(c => (
            <div key={c.id} className="webhook-card">
              <div className="webhook-card-info">
                <span className="webhook-card-name">{c.label}</span>
                {c.enabled
                  ? <span className="badge badge-nm">Enabled</span>
                  : <span className="badge badge-mp">Disabled</span>}
              </div>
              <div className="text-muted-sm">
                {c.target_url || 'Pull-only'}
                {c.target_url && !c.verify_tls && <span className="badge badge-mp" style={{ marginLeft: '0.4rem' }}>Insecure</span>}
              </div>
              <div className="text-muted-sm">
                Last used: {c.last_used_at ? new Date(c.last_used_at).toLocaleString() : 'Never'}
              </div>
              <div className="webhook-card-actions">
                <CredentialActions
                  credential={c}
                  onToggle={() => toggleEnabled.mutate({ id: c.id, enabled: !c.enabled })}
                  onToggleVerify={() => toggleVerifyTls.mutate({ id: c.id, verify_tls: !c.verify_tls })}
                  onRegenerate={() => regenerate.mutate(c.id)}
                  onTest={() => testPush.mutate(c.id)}
                  onDelete={() => confirmDelete(c)}
                  testMessage={testMessages[c.id]}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Label</th>
              <th>Target URL</th>
              <th>Last Used</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {credentials.map(c => (
              <tr key={c.id}>
                <td style={{ fontWeight: 600 }}>{c.label}</td>
                <td className="text-muted-sm">
                  {c.target_url || 'Pull-only'}
                  {c.target_url && !c.verify_tls && <span className="badge badge-mp" style={{ marginLeft: '0.4rem' }}>Insecure</span>}
                </td>
                <td className="text-muted-sm">
                  {c.last_used_at ? new Date(c.last_used_at).toLocaleString() : 'Never'}
                </td>
                <td>
                  {c.enabled
                    ? <span className="badge badge-nm">Enabled</span>
                    : <span className="badge badge-mp">Disabled</span>}
                </td>
                <td>
                  <CredentialActions
                    credential={c}
                    onToggle={() => toggleEnabled.mutate({ id: c.id, enabled: !c.enabled })}
                    onToggleVerify={() => toggleVerifyTls.mutate({ id: c.id, verify_tls: !c.verify_tls })}
                    onRegenerate={() => regenerate.mutate(c.id)}
                    onTest={() => testPush.mutate(c.id)}
                    onDelete={() => confirmDelete(c)}
                    testMessage={testMessages[c.id]}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ))}

      {showCreate && (
        <NewCredentialModal
          onClose={() => setShowCreate(false)}
          onCreated={(cred) => { setShowCreate(false); invalidate(); setRevealCredential(cred) }}
        />
      )}
      {revealCredential && (
        <SecretRevealModal credential={revealCredential} onClose={() => setRevealCredential(null)} />
      )}
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

import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Upload, Check, AlertTriangle, X } from 'lucide-react'
import api from '../api'

export default function ImportModal({ onClose }) {
  const qc = useQueryClient()
  const [text, setText] = useState('')
  const [form, setForm] = useState({ condition: 'NM', foil: false })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const run = async () => {
    if (!text.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await api.post('/collection/import', {
        list_text: text,
        condition: form.condition,
        foil: form.foil,
      })
      setResult(res.data)
      qc.invalidateQueries(['collection'])
    } catch (err) {
      setError(err.response?.data?.detail || 'Import failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}
        style={{ maxWidth: 580 }}>
        <h2>Bulk Import</h2>

        {!result && (
          <>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)',
              marginBottom: '1rem', lineHeight: 1.6 }}>
              Paste a Moxfield, MTGO, or plain text card list. Supported formats:
            </p>

            <div style={{ background: 'var(--bg)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius)', padding: '0.75rem 1rem',
              fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-muted)',
              marginBottom: '1rem', lineHeight: 1.8 }}>
              4 Lightning Bolt (CLU) 141<br />
              1 Eternal Witness (2XM) 172<br />
              2 Snapcaster Mage<br />
              1x Black Lotus
            </div>

            <div className="form-group">
              <label>Card List</label>
              <textarea
                rows={12}
                placeholder="Paste your card list here…"
                value={text}
                onChange={e => setText(e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: '0.85rem', resize: 'vertical' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem',
              marginBottom: '1rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Default Condition</label>
                <select value={form.condition}
                  onChange={e => setForm(f => ({ ...f, condition: e.target.value }))}>
                  {['NM','LP','MP','HP','DMG'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ marginBottom: 0, justifyContent: 'flex-end' }}>
                <label style={{ display: 'flex', alignItems: 'center',
                  gap: '0.5rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={form.foil}
                    onChange={e => setForm(f => ({ ...f, foil: e.target.checked }))}
                    style={{ width: 'auto' }} />
                  Mark all as Foil
                </label>
              </div>
            </div>

            {error && <div className="error">{error}</div>}

            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)',
              marginBottom: '1rem' }}>
              Each card is looked up on Scryfall. Large lists may take a moment.
            </div>

            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
              <button className="btn btn-primary" onClick={run}
                disabled={!text.trim() || loading}>
                {loading
                  ? <><span style={{ marginRight: '0.5rem' }}>⏳</span> Importing…</>
                  : <><Upload size={16} /> Import Cards</>}
              </button>
            </div>
          </>
        )}

        {result && (
          <>
            {/* Summary */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr',
              gap: '0.75rem', marginBottom: '1.5rem' }}>
              <div style={{ background: '#1a3a2a', border: '1px solid var(--success)',
                borderRadius: 'var(--radius)', padding: '1rem', textAlign: 'center' }}>
                <div style={{ fontSize: '2rem', fontWeight: 700,
                  color: 'var(--success)' }}>{result.imported}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--success)',
                  marginTop: '0.25rem' }}>Cards Imported</div>
              </div>
              <div style={{ background: result.skipped > 0 ? '#2a1a1a' : 'var(--surface2)',
                border: `1px solid ${result.skipped > 0 ? 'var(--danger)' : 'var(--border)'}`,
                borderRadius: 'var(--radius)', padding: '1rem', textAlign: 'center' }}>
                <div style={{ fontSize: '2rem', fontWeight: 700,
                  color: result.skipped > 0 ? 'var(--danger)' : 'var(--text-muted)' }}>
                  {result.skipped}
                </div>
                <div style={{ fontSize: '0.8rem',
                  color: result.skipped > 0 ? 'var(--danger)' : 'var(--text-muted)',
                  marginTop: '0.25rem' }}>Skipped</div>
              </div>
            </div>

            {/* Success message */}
            {result.imported > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem',
                background: '#1a3a2a', border: '1px solid var(--success)',
                borderRadius: 'var(--radius)', padding: '0.75rem 1rem',
                color: 'var(--success)', fontSize: '0.875rem', marginBottom: '1rem' }}>
                <Check size={16} />
                Successfully added {result.imported} card{result.imported !== 1 ? 's' : ''} to your collection.
              </div>
            )}

            {/* Errors list */}
            {result.errors.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontWeight: 600, fontSize: '0.85rem',
                  color: 'var(--danger)', marginBottom: '0.5rem',
                  display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <AlertTriangle size={14} /> Lines that could not be imported:
                </div>
                <div style={{ background: 'var(--bg)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)', padding: '0.75rem',
                  maxHeight: 180, overflowY: 'auto' }}>
                  {result.errors.map((e, i) => (
                    <div key={i} style={{ fontSize: '0.8rem', color: 'var(--danger)',
                      padding: '0.2rem 0', fontFamily: 'monospace' }}>
                      <X size={10} style={{ marginRight: '0.4rem', flexShrink: 0 }} />
                      {e}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setResult(null)}>
                Import More
              </button>
              <button className="btn btn-primary" onClick={onClose}>
                Done
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

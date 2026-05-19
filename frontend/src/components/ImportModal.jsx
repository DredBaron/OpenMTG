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
      <div className="modal modal-max-lg" onClick={e => e.stopPropagation()}>
        <h2>Bulk Import</h2>

        {!result && (
          <>
            <p className="import-description">
              Paste a Moxfield, MTGO, or plain text card list. Supported formats:
            </p>

            <div className="import-format-example">
              4 Lightning Bolt (CLU) 141<br />
              1 Eternal Witness (2XM) 172<br />
              2 Snapcaster Mage<br />
              1x Black Lotus
            </div>

            <div className="form-group">
              <label>Card List</label>
              <textarea
                rows={12}
                placeholder="Paste your card list here"
                value={text}
                onChange={e => setText(e.target.value)}
                className="import-textarea"
              />
            </div>

            <div className="import-options-grid">
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Default Condition</label>
                <select value={form.condition}
                  onChange={e => setForm(f => ({ ...f, condition: e.target.value }))}>
                  {['NM','LP','MP','HP','DMG'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group import-form-end">
                <label className="checkbox-label">
                  <input type="checkbox" checked={form.foil}
                    onChange={e => setForm(f => ({ ...f, foil: e.target.checked }))}
                    style={{ width: 'auto' }} />
                  Mark all as Foil
                </label>
              </div>
            </div>

            {error && <div className="error">{error}</div>}

            <div className="import-hint">
              Each card is looked up on Scryfall. Large lists may take a moment.
            </div>

            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
              <button className="btn btn-primary" onClick={run}
                disabled={!text.trim() || loading}>
                {loading
                  ? <>Importing</>
                  : <><Upload size={16} /> Import Cards</>}
              </button>
            </div>
          </>
        )}

        {result && (
          <>
            <div className="import-summary-grid">
              <div className="import-stat-box import-stat-success">
                <div className="import-stat-number" style={{ color: 'var(--success)' }}>{result.imported}</div>
                <div className="import-stat-label" style={{ color: 'var(--success)' }}>Cards Imported</div>
              </div>
              <div className={`import-stat-box import-stat-skipped${result.skipped > 0 ? ' has-errors' : ''}`}>
                <div className="import-stat-number" style={{ color: result.skipped > 0 ? 'var(--danger)' : 'var(--text-muted)' }}>
                  {result.skipped}
                </div>
                <div className="import-stat-label" style={{ color: result.skipped > 0 ? 'var(--danger)' : 'var(--text-muted)' }}>
                  Skipped
                </div>
              </div>
            </div>

            {result.imported > 0 && (
              <div className="import-success-banner">
                <Check size={16} />
                Successfully added {result.imported} card{result.imported !== 1 ? 's' : ''} to your collection.
              </div>
            )}

            {result.errors.length > 0 && (
              <div style={{ marginBottom: '1rem' }}>
                <div className="import-errors-header">
                  <AlertTriangle size={14} /> Lines that could not be imported:
                </div>
                <div className="import-errors-list">
                  {result.errors.map((e, i) => (
                    <div key={i} className="import-error-line">
                      <X size={10} className="import-error-icon" />
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

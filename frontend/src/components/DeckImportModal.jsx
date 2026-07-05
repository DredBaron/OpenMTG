import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Upload, Check, AlertTriangle, X } from 'lucide-react'

const FORMATS = ['Standard', 'Pioneer', 'Modern', 'Legacy', 'Vintage', 'Commander', 'Pauper', 'Draft', 'Other']

export default function DeckImportModal({ onClose, onImported }) {
  const [form, setForm] = useState({ name: '', format: '', description: '' })
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState({ total: 0, done: 0, card: '' })
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const run = async () => {
    if (!form.name.trim() || !text.trim()) return
    setLoading(true)
    setError('')
    setProgress({ total: 0, done: 0, card: '' })

    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/decks/import', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          name: form.name.trim(),
          format: form.format || null,
          description: form.description.trim() || null,
          list_text: text,
        }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Import failed')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done: streamDone, value } = await reader.read()
        if (streamDone) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))
            if (evt.type === 'start') {
              setProgress({ total: evt.total, done: 0, card: '' })
            } else if (evt.type === 'progress') {
              setProgress({ total: evt.total, done: evt.done, card: evt.card || '' })
            } else if (evt.type === 'done') {
              setResult(evt)
              onImported()
            }
          } catch { /* ignore malformed events */ }
        }
      }
    } catch (err) {
      setError(err.message || 'Import failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-max-lg" onClick={e => e.stopPropagation()}>
        <h2>Import Deck</h2>

        {!result && (
          <>
            <div className="form-group">
              <label>Deck Name</label>
              <input
                autoFocus
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              />
            </div>

            <div className="import-options-grid">
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Format</label>
                <select value={form.format}
                  onChange={e => setForm(f => ({ ...f, format: e.target.value }))}>
                  <option value="">Select format</option>
                  {FORMATS.map(f => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Description</label>
                <input value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
              </div>
            </div>

            <p className="import-description" style={{ marginTop: '1rem' }}>
              Paste a Moxfield, MTGO, or Arena deck list. Commander, Mainboard, and Sideboard section headers are recognized.
            </p>

            <p className="import-description" style={{ marginTop: '1rem' }}>
              Example Import:
            </p>

            <div className="import-format-example">
              Commander<br />
              1 Omnath, Locus of Creation (ZNR) 232<br />
              <br />
              Mainboard<br />
              4 Lightning Bolt (CLU) 141<br />
              1 Eternal Witness (2XM) 172<br />
              <br />
              Sideboard<br />
              2 Snapcaster Mage (WWK) 5
            </div>

            <div className="form-group">
              <label>Import Card List</label>
              <textarea
                rows={6}
                placeholder="Paste your deck list here"
                value={text}
                onChange={e => setText(e.target.value)}
                className="import-textarea"
              />
            </div>

            {error && <div className="error">{error}</div>}

            {loading ? (
              <div className="import-progress">
                <div className="import-progress-track">
                  <div
                    className="import-progress-fill"
                    style={{ width: progress.total > 0 ? `${(progress.done / progress.total) * 100}%` : '0%' }}
                  />
                </div>
                <div className="import-progress-label">
                  {progress.total > 0
                    ? `${progress.done} of ${progress.total}${progress.card ? ` - ${progress.card}` : ''}`
                    : 'Creating deck…'}
                </div>
              </div>
            ) : (
              <div className="import-hint">
                Each card is looked up on Scryfall. Large lists may take a moment.
              </div>
            )}

            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={onClose} disabled={loading}>Cancel</button>
              <button
                className="btn btn-primary"
                onClick={run}
                disabled={!form.name.trim() || !text.trim() || loading}>
                {loading ? 'Importing…' : <><Upload size={16} /> Import Deck</>}
              </button>
            </div>
          </>
        )}

        {result && (
          <>
            <div className="import-summary-grid">
              <div className="import-stat-box import-stat-success">
                <div className="import-stat-number" style={{ color: 'var(--success)' }}>
                  {result.imported}
                </div>
                <div className="import-stat-label" style={{ color: 'var(--success)' }}>
                  Cards Imported
                </div>
              </div>
              <div className={`import-stat-box import-stat-skipped${result.skipped > 0 ? ' has-errors' : ''}`}>
                <div className="import-stat-number"
                  style={{ color: result.skipped > 0 ? 'var(--danger)' : 'var(--text-muted)' }}>
                  {result.skipped}
                </div>
                <div className="import-stat-label"
                  style={{ color: result.skipped > 0 ? 'var(--danger)' : 'var(--text-muted)' }}>
                  Skipped
                </div>
              </div>
            </div>

            {result.imported > 0 && (
              <div className="import-success-banner">
                <Check size={16} />
                &ldquo;{result.deck_name}&rdquo; created with {result.imported} card{result.imported !== 1 ? 's' : ''}.
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
                      <X size={10} className="import-error-icon" /> {e}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={onClose}>Done</button>
              <Link
                to={`/decks/${result.deck_id}`}
                className="btn btn-primary"
                onClick={onClose}>
                View Deck
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

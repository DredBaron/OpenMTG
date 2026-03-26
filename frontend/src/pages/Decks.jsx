import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Plus, Trash2, ChevronRight } from 'lucide-react'
import api from '../api'

export default function Decks() {

  useEffect(() => { document.title = 'Decks - OpenMTG' }, [])

  const qc = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', format: '', description: '' })

  const { data: decks = [], isLoading } = useQuery({
    queryKey: ['decks'],
    queryFn: () => api.get('/decks').then(r => r.data),
  })

  const create = useMutation({
    mutationFn: () => api.post('/decks', form),
    onSuccess: () => {
      qc.invalidateQueries(['decks'])
      setShowCreate(false)
      setForm({ name: '', format: '', description: '' })
    }
  })

  const remove = useMutation({
    mutationFn: (id) => api.delete(`/decks/${id}`),
    onSuccess: () => qc.invalidateQueries(['decks']),
  })

  const FORMATS = ['Standard','Pioneer','Modern','Legacy','Vintage','Commander','Pauper','Draft','Other']

  return (
    <div>
      <div className="page-header">
        <h1>Decks</h1>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={18} /> New Deck
        </button>
      </div>

      {isLoading && <div className="loading">Loading decks…</div>}

      {!isLoading && decks.length === 0 && (
        <div className="empty-state">
          <p>No decks yet. Create your first one!</p>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {decks.map(deck => (
          <div key={deck.id} style={{ background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius)', padding: '1rem 1.25rem',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontWeight: 600 }}>{deck.name}</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                {deck.format && <span style={{ textTransform: 'capitalize' }}>{deck.format}</span>}
                {deck.description && ` · ${deck.description}`}
              </div>
            </div>
            <div className="flex-gap">
              <button className="btn btn-danger btn-sm"
                onClick={() => confirm('Delete this deck?') && remove.mutate(deck.id)}>
                <Trash2 size={14} />
              </button>
              <Link to={`/decks/${deck.id}`} className="btn btn-ghost btn-sm">
                Open <ChevronRight size={14} />
              </Link>
            </div>
          </div>
        ))}
      </div>

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h2>New Deck</h2>
            <div className="form-group">
              <label>Name</label>
              <input autoFocus value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>Format</label>
              <select value={form.format}
                onChange={e => setForm(f => ({ ...f, format: e.target.value }))}>
                <option value="">Select format…</option>
                {FORMATS.map(f => (
                  <option key={f} value={f} style={{ textTransform: 'capitalize' }}>{f}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea rows={2} value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setShowCreate(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => create.mutate()}
                disabled={!form.name || create.isPending}>
                {create.isPending ? 'Creating…' : 'Create Deck'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

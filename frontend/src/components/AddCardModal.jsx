import { useState } from 'react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import api from '../api'
import SetPicker from './SetPicker'

export default function AddCardModal({ onClose }) {
  const qc = useQueryClient()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState({ quantity: 1, condition: 'NM', foil: false, language: 'en' })
  const [searching, setSearching] = useState(false)

  const search = async () => {
    if (query.length < 2) return
    setSearching(true)
    try {
      const res = await api.get(`/cards/search?q=${encodeURIComponent(query)}`)
      setResults(res.data)
    } finally {
      setSearching(false)
    }
  }

  const add = useMutation({
    mutationFn: () => api.post('/collection', { scryfall_id: selected.scryfall_id, ...form }),
    onSuccess: () => { qc.invalidateQueries(['collection']); onClose() }
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Add Card</h2>
        <div className="search-bar">
          <input placeholder="Search Scryfall…" value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()} />
          <button className="btn btn-primary" onClick={search} disabled={searching}>
            <Search size={16} />
          </button>
        </div>

        {results.length > 0 && !selected && (
          <div style={{ maxHeight: 240, overflowY: 'auto', marginBottom: '1rem' }}>
            {results.map(card => (
              <div key={card.scryfall_id}
                onClick={() => setSelected(card)}
                style={{
                  display: 'flex', gap: '0.75rem', alignItems: 'center',
                  padding: '0.5rem', borderRadius: 'var(--radius)',
                  cursor: 'pointer', borderBottom: '1px solid var(--border)'
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--surface2)'}
                onMouseLeave={e => e.currentTarget.style.background = ''}>
                {card.image_uri &&
                  <img src={card.image_uri} alt={card.name} style={{ width: 36, borderRadius: 4 }} />}
                <div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{card.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {card.set_name} · {card.rarity}
                    {card.price_usd && ` · $${card.price_usd}`}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {selected && (
          <>
            <div className="card-preview-block">
              {selected.image_uri &&
                <img src={selected.image_uri} alt={selected.name} style={{ width: 48, borderRadius: 4 }} />}
              <div>
                <div style={{ fontWeight: 600 }}>{selected.name}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{selected.set_name}</div>
                <button onClick={() => setSelected(null)}
                  style={{ fontSize: '0.75rem', color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                  Change card
                </button>
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <SetPicker card={selected} onSelect={(printing) => {
                setSelected(prev => ({
                  ...prev,
                  scryfall_id:      printing.scryfall_id,
                  set_code:         printing.set_code,
                  set_name:         printing.set_name,
                  collector_number: printing.collector_number,
                  rarity:           printing.rarity,
                  image_uri:        printing.image_uri,
                  price_usd:        printing.price_usd,
                  price_usd_foil:   printing.price_usd_foil,
                }))
              }} />
            </div>

            <div className="form-grid-2col">
              <div className="form-group">
                <label>Quantity</label>
                <input type="number" min={1} value={form.quantity}
                  onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) }))} />
              </div>
              <div className="form-group">
                <label>Condition</label>
                <select value={form.condition} onChange={e => setForm(f => ({ ...f, condition: e.target.value }))}>
                  {['NM','LP','MP','HP','DMG'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Language</label>
                <input value={form.language} onChange={e => setForm(f => ({ ...f, language: e.target.value }))} />
              </div>
              <div className="form-group" style={{ justifyContent: 'flex-end' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={form.foil}
                    onChange={e => setForm(f => ({ ...f, foil: e.target.checked }))}
                    style={{ width: 'auto' }} />
                  Foil
                </label>
              </div>
            </div>
          </>
        )}

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          {selected &&
            <button className="btn btn-primary" onClick={() => add.mutate()} disabled={add.isPending}>
              {add.isPending ? 'Adding…' : 'Add to Collection'}
            </button>}
        </div>
      </div>
    </div>
  )
}

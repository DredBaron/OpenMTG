import { useState, useRef, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Search, Plus, Check } from 'lucide-react'
import api from '../api'
import SetPicker from '../components/SetPicker'

export default function Scanner() {

  useEffect(() => { document.title = 'Quick Add - OpenMTG' }, [])

  const qc = useQueryClient()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState({ quantity: 1, condition: 'NM', foil: false, language: 'en' })
  const [searching, setSearching] = useState(false)
  const [added, setAdded] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)

  const search = async () => {
    if (query.length < 2) return
    setSearching(true)
    setError('')
    setResults([])
    setSelected(null)
    try {
      const res = await api.get(`/cards/named?name=${encodeURIComponent(query)}`)
      // Exact/fuzzy single match
      setSelected(res.data)
    } catch {
      // Fall back to search results list
      try {
        const res = await api.get(`/cards/search?q=${encodeURIComponent(query)}`)
        setResults(res.data)
      } catch {
        setError('No cards found.')
      }
    } finally {
      setSearching(false)
    }
  }

  const addCard = async () => {
    await api.post('/collection', { scryfall_id: selected.scryfall_id, ...form })
    qc.invalidateQueries(['collection'])
    setAdded(true)
    setQuery('')
    setSelected(null)
    setResults([])
    setForm({ quantity: 1, condition: 'NM', foil: false, language: 'en' })
    setTimeout(() => setAdded(false), 2000)
    inputRef.current?.focus()
  }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <div className="page-header">
        <h1>Quick Add</h1>
      </div>

      {added && (
        <div style={{ background: '#1a3a2a', border: '1px solid var(--success)',
          borderRadius: 'var(--radius)', padding: '0.75rem 1rem', marginBottom: '1rem',
          color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Check size={16} /> Card added to collection!
        </div>
      )}

      {/* Search bar */}
      <div className="search-bar" style={{ marginBottom: '1.5rem' }}>
        <input
          ref={inputRef}
          autoFocus
          placeholder="Type a card name…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          style={{ fontSize: '1.1rem', padding: '0.75rem 1rem' }}
        />
        <button className="btn btn-primary" onClick={search} disabled={searching}
          style={{ padding: '0.75rem 1.25rem' }}>
          {searching ? '…' : <Search size={20} />}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {/* Multi-result list */}
      {results.length > 0 && !selected && (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius)', overflow: 'hidden', marginBottom: '1.5rem' }}>
          {results.map(card => (
            <div key={card.scryfall_id}
              onClick={() => { setSelected(card); setResults([]) }}
              style={{ display: 'flex', gap: '0.75rem', alignItems: 'center',
                padding: '0.75rem 1rem', cursor: 'pointer',
                borderBottom: '1px solid var(--border)' }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--surface2)'}
              onMouseLeave={e => e.currentTarget.style.background = ''}>
              {card.image_uri &&
                <img src={card.image_uri} alt={card.name}
                  style={{ width: 40, borderRadius: 4, flexShrink: 0 }} />}
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{card.name}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {card.set_name} · {card.collector_number} · {card.rarity}
                </div>
              </div>
              {card.price_usd &&
                <div style={{ color: 'var(--gold)', fontWeight: 600, fontSize: '0.9rem' }}>
                  ${card.price_usd}
                </div>}
            </div>
          ))}
        </div>
      )}

      {/* Selected card */}
      {selected && (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--accent)',
          borderRadius: 'var(--radius)', overflow: 'hidden' }}>
          <div style={{ display: 'flex', gap: '1rem', padding: '1rem',
            borderBottom: '1px solid var(--border)' }}>
            {selected.image_uri &&
              <img src={selected.image_uri} alt={selected.name}
                style={{ width: 120, borderRadius: 6, flexShrink: 0 }} />}
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '0.25rem' }}>
                {selected.name}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                {selected.set_name} · #{selected.collector_number}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                {selected.type_line}
              </div>
              {selected.oracle_text &&
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)',
                  fontStyle: 'italic', lineHeight: 1.5 }}>
                  {selected.oracle_text}
                </div>}
              {selected.price_usd &&
                <div style={{ color: 'var(--gold)', fontWeight: 700,
                  fontSize: '1rem', marginTop: '0.5rem' }}>
                  ${selected.price_usd}
                  {selected.price_usd_foil &&
                    <span style={{ fontSize: '0.8rem', marginLeft: '0.5rem', color: '#c09af0' }}>
                      ${selected.price_usd_foil} foil
                    </span>}
                </div>}
            </div>
          </div>

          <div style={{ padding: '1rem' }}>

            {/* Set picker */}
            <div style={{ marginBottom: '1rem' }}>
              <SetPicker
                card={selected}
                onSelect={(printing) => {
                  // Merge the chosen printing's fields into selected
                  // so the card image and price update live
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
                }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem',
              marginBottom: '0.75rem' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Quantity</label>
                <input type="number" min={1} value={form.quantity}
                  onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) }))} />
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Condition</label>
                <select value={form.condition}
                  onChange={e => setForm(f => ({ ...f, condition: e.target.value }))}>
                  {['NM','LP','MP','HP','DMG'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label>Language</label>
                <input value={form.language}
                  onChange={e => setForm(f => ({ ...f, language: e.target.value }))} />
              </div>
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem',
              fontSize: '0.875rem', cursor: 'pointer', marginBottom: '1rem' }}>
              <input type="checkbox" checked={form.foil}
                onChange={e => setForm(f => ({ ...f, foil: e.target.checked }))}
                style={{ width: 'auto' }} />
              Foil
            </label>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="btn btn-ghost" onClick={() => setSelected(null)}
                style={{ flex: 1, justifyContent: 'center' }}>
                Back
              </button>
              <button className="btn btn-primary" onClick={addCard}
                style={{ flex: 2, justifyContent: 'center', padding: '0.75rem' }}>
                <Plus size={18} /> Add to Collection
              </button>
            </div>
          </div>
        </div>
      )}

      {!selected && results.length === 0 && !added && (
        <div className="empty-state">
          <p>Search for any Magic card by name.</p>
          <p>Scryfall's fuzzy search handles typos and partial names.</p>
        </div>
      )}
    </div>
  )
}

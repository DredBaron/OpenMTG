import { useState, useRef, useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Search, Plus, Check } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import api from '../api'
import SetPicker from '../components/SetPicker'
import { useCurrency } from '../hooks/useCurrency'
import { formatPrice, resolvePrice } from '../utils/currency'

export default function Scanner() {
  const { scannerEnabled } = useAuth()

  useEffect(() => { document.title = 'Card Search - OpenMTG' }, [])

  const qc = useQueryClient()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState({ quantity: 1, condition: 'NM', foil: false, language: 'en' })
  const [searching, setSearching] = useState(false)
  const [added, setAdded] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)
  const { currency, market } = useCurrency()

  const search = async () => {
    if (query.length < 2) return
    setSearching(true)
    setError('')
    setResults([])
    setSelected(null)
    try {
      const res = await api.get(`/cards/named?name=${encodeURIComponent(query)}`)
      setSelected(res.data)
    } catch {
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

  if (!scannerEnabled) return <Navigate to="/collection" replace />

  return (
    <div className="scanner-page">
      <div className="page-header">
        <h1>Card Search</h1>
      </div>

      {added && (
        <div className="scan-success-banner">
          <Check size={16} /> Card added to collection!
        </div>
      )}

      <div className="search-bar" style={{ marginBottom: '1.5rem' }}>
        <input
          ref={inputRef}
          autoFocus
          placeholder="Type a card name"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          className="search-input-lg"
        />
        <button className="btn btn-primary search-btn-lg" onClick={search} disabled={searching}>
          {searching ? '...' : <Search size={20} />}
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {results.length > 0 && !selected && (
        <div className="result-list">
          {results.map(card => (
            <div key={card.scryfall_id}
              onClick={() => { setSelected(card); setResults([]) }}
              className="result-item">
              {card.image_uri &&
                <img src={card.image_uri} alt={card.name} className="result-thumb" />}
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{card.name}</div>
                <div className="text-muted-sm">
                  {card.set_name} | {card.collector_number} | {card.rarity}
                </div>
              </div>
              {resolvePrice(card, currency, false, market) != null &&
                <div className="result-price">
                  {formatPrice(resolvePrice(card, currency, false, market), currency, market)}
                </div>}
            </div>
          ))}
        </div>
      )}

      {selected && (
        <div className="selected-panel">
          <div className="selected-top">
            {selected.image_uri &&
              <img src={selected.image_uri} alt={selected.name} className="selected-img-lg" />}
            <div style={{ flex: 1 }}>
              <div className="selected-card-name">{selected.name}</div>
              <div className="selected-card-meta">
                {selected.set_name} | #{selected.collector_number}
              </div>
              <div className="selected-card-meta-b">{selected.type_line}</div>
              {selected.oracle_text &&
                <div className="selected-card-oracle">{selected.oracle_text}</div>}
              {resolvePrice(selected, currency, false, market) != null &&
                <div className="selected-card-price">
                  {formatPrice(resolvePrice(selected, currency, false, market), currency, market)}
                  {resolvePrice(selected, currency, true, market) != null &&
                    <span className="foil-price-note">
                      {formatPrice(resolvePrice(selected, currency, true, market), currency, market)} foil
                    </span>}
                </div>}
            </div>
          </div>

          <div className="selected-body">

            <div style={{ marginBottom: '1rem' }}>
              <SetPicker
                card={selected}
                onSelect={(printing) => {
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
                    price_eur:        printing.price_eur,
                    price_eur_foil:   printing.price_eur_foil,
                  }))
                }}
              />
            </div>

            <div className="form-grid-3col">
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

            <label className="scanner-foil-label">
              <input type="checkbox" checked={form.foil}
                onChange={e => setForm(f => ({ ...f, foil: e.target.checked }))}
                style={{ width: 'auto' }} />
              Foil
            </label>

            <div className="action-row">
              <button className="btn btn-ghost scanner-btn-back" onClick={() => setSelected(null)}>
                Back
              </button>
              <button className="btn btn-primary scanner-btn-add" onClick={addCard}>
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

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Pencil, Trash2, Download, Upload } from 'lucide-react'
import api from '../api'
import SetPicker from '../components/SetPicker'
import ImportModal from '../components/ImportModal'

function AddCardModal({ onClose }) {
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
                style={{ display: 'flex', gap: '0.75rem', alignItems: 'center',
                  padding: '0.5rem', borderRadius: 'var(--radius)', cursor: 'pointer',
                  borderBottom: '1px solid var(--border)' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--surface2)'}
                onMouseLeave={e => e.currentTarget.style.background = ''}>
                {card.image_uri &&
                  <img src={card.image_uri} alt={card.name}
                    style={{ width: 36, borderRadius: 4 }} />}
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
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center',
              padding: '0.75rem', background: 'var(--surface2)',
              borderRadius: 'var(--radius)', marginBottom: '1rem' }}>
              {selected.image_uri &&
                <img src={selected.image_uri} alt={selected.name}
                  style={{ width: 48, borderRadius: 4 }} />}
              <div>
                <div style={{ fontWeight: 600 }}>{selected.name}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{selected.set_name}</div>
                <button onClick={() => setSelected(null)}
                  style={{ fontSize: '0.75rem', color: 'var(--accent)',
                    background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                  Change card
                </button>
              </div>
            </div>

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
                  }))
                }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div className="form-group">
                <label>Quantity</label>
                <input type="number" min={1} value={form.quantity}
                  onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) }))} />
              </div>
              <div className="form-group">
                <label>Condition</label>
                <select value={form.condition}
                  onChange={e => setForm(f => ({ ...f, condition: e.target.value }))}>
                  {['NM','LP','MP','HP','DMG'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Language</label>
                <input value={form.language}
                  onChange={e => setForm(f => ({ ...f, language: e.target.value }))} />
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
            <button className="btn btn-primary" onClick={() => add.mutate()}
              disabled={add.isPending}>
              {add.isPending ? 'Adding…' : 'Add to Collection'}
            </button>}
        </div>
      </div>
    </div>
  )
}

function EditModal({ entry, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    quantity: entry.quantity,
    condition: entry.condition,
    foil: entry.foil,
    language: entry.language,
    notes: entry.notes || '',
    scryfall_id: entry.card.scryfall_id,
  })
  const [card, setCard] = useState(entry.card)

  const save = useMutation({
    mutationFn: () => api.patch(`/collection/${entry.id}`, form),
    onSuccess: () => { qc.invalidateQueries(['collection']); onClose() }
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Edit: {entry.card.name}</h2>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center',
          padding: '0.75rem', background: 'var(--surface2)',
          borderRadius: 'var(--radius)', marginBottom: '1rem' }}>
          {card.image_uri &&
            <img src={card.image_uri} alt={card.name}
              style={{ width: 48, borderRadius: 4, flexShrink: 0 }} />}
          <div>
            <div style={{ fontWeight: 600 }}>{card.name}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {card.set_name} · #{card.collector_number}
            </div>
            {card.price_usd &&
              <div style={{ fontSize: '0.8rem', color: 'var(--gold)' }}>
                ${card.price_usd}
                {card.price_usd_foil &&
                  <span style={{ color: '#c09af0', marginLeft: '0.4rem' }}>
                    ${card.price_usd_foil} foil
                  </span>}
              </div>}
          </div>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <SetPicker
            card={card}
            onSelect={(printing) => {
              setCard(prev => ({
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
              setForm(f => ({ ...f, scryfall_id: printing.scryfall_id }))
            }}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <div className="form-group">
            <label>Quantity</label>
            <input type="number" min={1} value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) }))} />
          </div>
          <div className="form-group">
            <label>Condition</label>
            <select value={form.condition}
              onChange={e => setForm(f => ({ ...f, condition: e.target.value }))}>
              {['NM','LP','MP','HP','DMG'].map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Language</label>
            <input value={form.language}
              onChange={e => setForm(f => ({ ...f, language: e.target.value }))} />
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

        <div className="form-group">
          <label>Notes</label>
          <textarea rows={2} value={form.notes}
            onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
        </div>

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => save.mutate()}
            disabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Collection() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [editing, setEditing] = useState(null)

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['collection', search],
    queryFn: () => api.get(`/collection${search ? `?search=${search}` : ''}`).then(r => r.data),
  })

  const remove = useMutation({
    mutationFn: (id) => api.delete(`/collection/${id}`),
    onSuccess: () => qc.invalidateQueries(['collection']),
  })

  const totalValue = entries.reduce((sum, e) => {
    const price = e.foil ? (e.card.price_usd_foil || e.card.price_usd) : e.card.price_usd
    return sum + (price || 0) * e.quantity
  }, 0)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Collection</h1>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            {entries.length} entries · Est. value{' '}
            <span style={{ color: 'var(--gold)' }}>${totalValue.toFixed(2)}</span>
          </div>
        </div>
        <div className="flex-gap">
          <a href="/api/export/collection/csv"
            className="btn btn-ghost btn-sm" download>
            <Download size={15} /> CSV
          </a>
          <a href="/api/export/collection/json"
            className="btn btn-ghost btn-sm" download>
            <Download size={15} /> JSON
          </a>
          <button className="btn btn-ghost" onClick={() => setShowImport(true)}>
            <Upload size={18} /> Import
          </button>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
            <Plus size={18} /> Add Card
          </button>
        </div>
      </div>

      <div className="search-bar">
        <input placeholder="Filter by name…" value={search}
          onChange={e => setSearch(e.target.value)} />
      </div>

      {isLoading && <div className="loading">Loading collection…</div>}

      {!isLoading && entries.length === 0 && (
        <div className="empty-state">
          <p>Your collection is empty.</p>
          <p>Add cards or use the Quick Add to get started.</p>
        </div>
      )}

      {entries.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th></th>
              <th>Card</th>
              <th>Set</th>
              <th>Qty</th>
              <th>Condition</th>
              <th>Price</th>
              <th>Notes</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {entries.map(entry => (
              <tr key={entry.id}>
                <td style={{ width: 40 }}>
                  {entry.card.image_uri &&
                    <img src={entry.card.image_uri} alt={entry.card.name}
                      style={{ width: 36, borderRadius: 4 }} />}
                </td>
                <td>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{entry.card.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {entry.card.mana_cost} · {entry.card.type_line}
                  </div>
                </td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {entry.card.set_name}<br />#{entry.card.collector_number}
                </td>
                <td>{entry.quantity}</td>
                <td>
                  <span className={`badge badge-${entry.condition.toLowerCase()}`}>
                    {entry.condition}
                  </span>
                  {entry.foil && <span className="badge badge-foil" style={{ marginLeft: 4 }}>Foil</span>}
                </td>
                <td style={{ color: 'var(--gold)' }}>
                  {entry.card.price_usd ? `$${entry.card.price_usd}` : '—'}
                </td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: 140 }}>
                  {entry.notes}
                </td>
                <td>
                  <div className="flex-gap">
                    <button className="btn btn-ghost btn-sm" onClick={() => setEditing(entry)}>
                      <Pencil size={14} />
                    </button>
                    <button className="btn btn-danger btn-sm"
                      onClick={() => confirm('Remove this card?') && remove.mutate(entry.id)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {showAdd && <AddCardModal onClose={() => setShowAdd(false)} />}
      {editing && <EditModal entry={editing} onClose={() => setEditing(null)} />}
      {showImport && <ImportModal onClose={() => setShowImport(false)} />}
    </div>
  )
}

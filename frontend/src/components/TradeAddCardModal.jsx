import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import api from '../api'

export default function TradeAddCardModal({ existingIds = [], onAdd, onClose }) {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)
  const [qty, setQty] = useState(1)

  const { data: entries = [] } = useQuery({
    queryKey: ['collection'],
    queryFn: () => api.get('/collection').then(r => r.data),
    staleTime: Infinity,
  })

  const filtered = entries
    .filter(e => !existingIds.includes(e.id))
    .filter(e => !search || e.card.name.toLowerCase().includes(search.toLowerCase()))
    .slice(0, 60)

  const handleAdd = () => {
    if (!selected) return
    onAdd({ ...selected, tradeQty: qty })
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 440, maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}
        onClick={e => e.stopPropagation()}>
        <h2>Add Card to Trade</h2>

        <div className="search-bar" style={{ margin: '0 0 0.75rem' }}>
          <input
            placeholder="Search your collection"
            value={search}
            onChange={e => { setSearch(e.target.value); setSelected(null) }}
            autoFocus
          />
        </div>

        <div className="trade-add-list" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
          {filtered.length === 0 && (
            <div className="empty-state" style={{ padding: '1rem' }}>
              <p>No cards found.</p>
            </div>
          )}
          {filtered.map(entry => (
            <button
              key={entry.id}
              className={`trade-add-item${selected?.id === entry.id ? ' selected' : ''}`}
              onClick={() => { setSelected(entry); setQty(1) }}
            >
              {entry.card.image_uri && (
                <img src={entry.card.image_uri} alt={entry.card.name} className="trade-add-thumb" />
              )}
              <div className="trade-add-info">
                <div className="trade-add-name">{entry.card.name}</div>
                <div className="text-muted-xs">
                  {entry.condition}{entry.foil ? ' · Foil' : ''} · Qty: {entry.quantity}
                </div>
              </div>
            </button>
          ))}
        </div>

        {selected && (
          <div className="form-group" style={{ marginTop: '0.75rem', marginBottom: 0 }}>
            <label>Quantity to trade (max {selected.quantity})</label>
            <input
              type="number"
              min={1}
              max={selected.quantity}
              value={qty}
              onChange={e => setQty(Math.min(selected.quantity, Math.max(1, parseInt(e.target.value) || 1)))}
            />
          </div>
        )}

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={!selected} onClick={handleAdd}>
            Add to Trade
          </button>
        </div>
      </div>
    </div>
  )
}

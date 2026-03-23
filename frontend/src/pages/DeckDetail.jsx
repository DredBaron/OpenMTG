import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Download, Search } from 'lucide-react'
import api from '../api'

function AddCardModal({ deckId, onClose }) {
  const qc = useQueryClient()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState({ quantity: 1, is_sideboard: false, is_commander: false })
  const [searching, setSearching] = useState(false)

  const search = async () => {
    if (query.length < 2) return
    setSearching(true)
    try {
      const res = await api.get(`/cards/search?q=${encodeURIComponent(query)}`)
      setResults(res.data)
    } finally { setSearching(false) }
  }

  const add = useMutation({
    mutationFn: () => api.post(`/decks/${deckId}/cards`, { scryfall_id: selected.scryfall_id, ...form }),
    onSuccess: () => { qc.invalidateQueries(['deck', deckId]); onClose() }
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Add Card to Deck</h2>
        <div className="search-bar">
          <input placeholder="Search Scryfall…" value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()} />
          <button className="btn btn-primary" onClick={search} disabled={searching}>
            <Search size={16} />
          </button>
        </div>
        {results.length > 0 && !selected && (
          <div style={{ maxHeight: 200, overflowY: 'auto', marginBottom: '1rem' }}>
            {results.map(card => (
              <div key={card.scryfall_id} onClick={() => setSelected(card)}
                style={{ padding: '0.5rem', cursor: 'pointer', borderBottom: '1px solid var(--border)',
                  display: 'flex', gap: '0.5rem', alignItems: 'center' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--surface2)'}
                onMouseLeave={e => e.currentTarget.style.background = ''}>
                <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{card.name}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {card.set_code?.toUpperCase()} · {card.mana_cost}
                </div>
              </div>
            ))}
          </div>
        )}
        {selected && (
          <>
            <div style={{ background: 'var(--surface2)', padding: '0.75rem',
              borderRadius: 'var(--radius)', marginBottom: '1rem', fontWeight: 600 }}>
              {selected.name}
              <button onClick={() => setSelected(null)}
                style={{ marginLeft: '0.75rem', fontSize: '0.75rem', color: 'var(--accent)',
                  background: 'none', border: 'none', cursor: 'pointer' }}>
                Change
              </button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
              <div className="form-group">
                <label>Quantity</label>
                <input type="number" min={1} value={form.quantity}
                  onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) }))} />
              </div>
              <div className="form-group" style={{ justifyContent: 'flex-end' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={form.is_sideboard}
                    onChange={e => setForm(f => ({ ...f, is_sideboard: e.target.checked }))}
                    style={{ width: 'auto' }} />
                  Sideboard
                </label>
              </div>
              <div className="form-group" style={{ justifyContent: 'flex-end' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                  <input type="checkbox" checked={form.is_commander}
                    onChange={e => setForm(f => ({ ...f, is_commander: e.target.checked }))}
                    style={{ width: 'auto' }} />
                  Commander
                </label>
              </div>
            </div>
          </>
        )}
        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          {selected && <button className="btn btn-primary" onClick={() => add.mutate()}
            disabled={add.isPending}>
            {add.isPending ? 'Adding…' : 'Add to Deck'}
          </button>}
        </div>
      </div>
    </div>
  )
}

function CardSection({ title, cards, deckId }) {
  const qc = useQueryClient()
  const remove = useMutation({
    mutationFn: (cardId) => api.delete(`/decks/${deckId}/cards/${cardId}`),
    onSuccess: () => qc.invalidateQueries(['deck', deckId]),
  })

  if (cards.length === 0) return null
  const total = cards.reduce((s, c) => s + c.quantity, 0)

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <div style={{ fontWeight: 600, color: 'var(--text-muted)', fontSize: '0.8rem',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
        {title} ({total})
      </div>
      {cards.map(dc => (
        <div key={dc.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem',
          padding: '0.4rem 0', borderBottom: '1px solid var(--border)' }}>
          <span style={{ width: 24, textAlign: 'right', color: 'var(--text-muted)',
            fontSize: '0.875rem' }}>{dc.quantity}</span>
          <span style={{ flex: 1, fontSize: '0.875rem' }}>{dc.card.name}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{dc.card.mana_cost}</span>
          {dc.card.price_usd &&
            <span style={{ fontSize: '0.75rem', color: 'var(--gold)' }}>${dc.card.price_usd}</span>}
          <button className="btn btn-ghost btn-sm" onClick={() => remove.mutate(dc.id)}>
            <Trash2 size={12} />
          </button>
        </div>
      ))}
    </div>
  )
}

export default function DeckDetail() {
  const { id } = useParams()
  const [showAdd, setShowAdd] = useState(false)

  const { data: deck, isLoading } = useQuery({
    queryKey: ['deck', id],
    queryFn: () => api.get(`/decks/${id}`).then(r => r.data),
    enabled: !!id && id !== 'undefined',
    retry: false,
    refetchOnWindowFocus: false,
  })

  if (!id || id === 'undefined') return null
  if (isLoading) return <div className="loading">Loading deck…</div>
  if (!deck) return <div className="empty-state"><p>Deck not found.</p></div>

  const commander = deck.cards.filter(c => c.is_commander)
  const mainboard  = deck.cards.filter(c => !c.is_sideboard && !c.is_commander)
  const sideboard  = deck.cards.filter(c => c.is_sideboard)
  const totalCards = mainboard.reduce((s, c) => s + c.quantity, 0)
  const totalValue = deck.cards.reduce((s, c) => s + (c.card.price_usd || 0) * c.quantity, 0)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{deck.name}</h1>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            {deck.format && <span style={{ textTransform: 'capitalize' }}>{deck.format} · </span>}
            {totalCards} cards · Est.{' '}
            <span style={{ color: 'var(--gold)' }}>${totalValue.toFixed(2)}</span>
          </div>
        </div>
        <div className="flex-gap">
          <a href={`/api/export/deck/${id}/moxfield`} className="btn btn-ghost btn-sm" download>
            <Download size={15} /> Moxfield
          </a>
          <a href={`/api/export/deck/${id}/json`} className="btn btn-ghost btn-sm" download>
            <Download size={15} /> JSON
          </a>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
            <Plus size={18} /> Add Card
          </button>
        </div>
      </div>

      <CardSection title="Commander" cards={commander} deckId={id} />
      <CardSection title="Mainboard" cards={mainboard} deckId={id} />
      <CardSection title="Sideboard" cards={sideboard} deckId={id} />

      {deck.cards.length === 0 && (
        <div className="empty-state">
          <p style={{ fontSize: '2rem' }}>🃏</p>
          <p>No cards yet. Add some!</p>
        </div>
      )}

      {showAdd && <AddCardModal deckId={id} onClose={() => setShowAdd(false)} />}
    </div>
  )
}

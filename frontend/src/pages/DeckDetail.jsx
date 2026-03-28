import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Download, Search } from 'lucide-react'
import { downloadFile } from '../utils/downloadFile';
import api from '../api'
import ConfirmModal from '../components/ConfirmModal'

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
          <input
            placeholder="Search Scryfall…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()}
          />
          <button className="btn btn-primary" onClick={search} disabled={searching}>
            <Search size={16} />
          </button>
        </div>

        {results.length > 0 && !selected && (
          <div style={{ maxHeight: 200, overflowY: 'auto', marginBottom: '1rem' }}>
            {results.map(card => (
              <div
                key={card.scryfall_id}
                onClick={() => setSelected(card)}
                style={{
                  padding: '0.5rem',
                  cursor: 'pointer',
                  borderBottom: '1px solid var(--border)',
                  display: 'flex',
                  gap: '0.5rem',
                  alignItems: 'center'
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--surface2)'}
                onMouseLeave={e => e.currentTarget.style.background = ''}
              >
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
            <div style={{
              background: 'var(--surface2)',
              padding: '0.75rem',
              borderRadius: 'var(--radius)',
              marginBottom: '1rem',
              fontWeight: 600
            }}>
              {selected.name}
              <button
                onClick={() => setSelected(null)}
                style={{
                  marginLeft: '0.75rem',
                  fontSize: '0.75rem',
                  color: 'var(--accent)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer'
                }}
              >
                Change
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
              <div className="form-group">
                <label>Quantity</label>
                <input
                  type="number"
                  min={1}
                  value={form.quantity}
                  onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) }))}
                />
              </div>

              <div className="form-group" style={{ justifyContent: 'flex-end' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={form.is_sideboard}
                    onChange={e => setForm(f => ({ ...f, is_sideboard: e.target.checked }))}
                    style={{ width: 'auto' }}
                  />
                  Sideboard
                </label>
              </div>

              <div className="form-group" style={{ justifyContent: 'flex-end' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={form.is_commander}
                    onChange={e => setForm(f => ({ ...f, is_commander: e.target.checked }))}
                    style={{ width: 'auto' }}
                  />
                  Commander
                </label>
              </div>
            </div>
          </>
        )}

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          {selected && (
            <button className="btn btn-primary" onClick={() => add.mutate()} disabled={add.isPending}>
              {add.isPending ? 'Adding…' : 'Add to Deck'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function EditCardModal({ cardEntry, deckId, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    quantity: cardEntry.quantity,
    is_sideboard: cardEntry.is_sideboard,
    is_commander: cardEntry.is_commander,
    scryfall_id: cardEntry.card.scryfall_id,
  })
  const [card] = useState(cardEntry.card)

  const save = useMutation({
    mutationFn: () => api.patch(`/decks/${deckId}/cards/${cardEntry.id}`, form),
    onSuccess: () => { qc.invalidateQueries(['deck', deckId]); onClose() }
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Edit Card: {card.name}</h2>

        <div style={{
          background: 'var(--surface2)',
          padding: '0.75rem',
          borderRadius: 'var(--radius)',
          marginBottom: '1rem',
          fontWeight: 600
        }}>
          {card.name}
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: '0.75rem',
          marginBottom: '1rem'
        }}>
          <div className="form-group">
            <label>Quantity</label>
            <input
              type="number"
              min={1}
              value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) }))}
            />
          </div>

          <div className="form-group" style={{ justifyContent: 'flex-end' }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              cursor: 'pointer'
            }}>
              <input
                type="checkbox"
                checked={form.is_sideboard}
                onChange={e => setForm(f => ({ ...f, is_sideboard: e.target.checked }))}
                style={{ width: 'auto' }}
              />
              Sideboard
            </label>
          </div>

          <div className="form-group" style={{ justifyContent: 'flex-end' }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              cursor: 'pointer'
            }}>
              <input
                type="checkbox"
                checked={form.is_commander}
                onChange={e => setForm(f => ({ ...f, is_commander: e.target.checked }))}
                style={{ width: 'auto' }}
              />
              Commander
            </label>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

function CardSection({ title, cards, deckId, selectedIds, toggleSelect }) {
  const [editing, setEditing] = useState(null)
  const qc = useQueryClient()

  const remove = useMutation({
    mutationFn: (cardId) => api.delete(`/decks/${deckId}/cards/${cardId}`),
    onSuccess: () => qc.invalidateQueries(['deck', deckId]),
  })

  if (!cards || cards.length === 0) return null

  const total = cards.reduce((sum, c) => sum + c.quantity, 0)
  const allSelected = cards.length > 0 && cards.every(c => selectedIds.has(c.id))
  const toggleAll = () => cards.forEach(c => {
    if (allSelected !== selectedIds.has(c.id)) return
    toggleSelect(c.id)
  })

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        fontWeight: 600,
        color: 'var(--text-muted)',
        fontSize: '0.8rem',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        marginBottom: '0.5rem'
      }}>
        <span>{title} ({total})</span>
        <input type="checkbox" checked={allSelected} onChange={toggleAll}
          style={{ width: 'auto', cursor: 'pointer' }} title="Select all in section" />
      </div>

      {cards.map(dc => (
        <div key={dc.id} style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          padding: '0.4rem 0',
          borderBottom: '1px solid var(--border)'
        }}>
          <span style={{
            width: 24,
            textAlign: 'right',
            color: 'var(--text-muted)',
            fontSize: '0.875rem'
          }}>
            {dc.quantity}
          </span>

          <span style={{ flex: 1, fontSize: '0.875rem' }}>{dc.card.name}</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{dc.card.mana_cost}</span>

          {dc.card.price_usd && (
            <span style={{ fontSize: '0.75rem', color: 'var(--gold)' }}>
              ${dc.card.price_usd}
            </span>
          )}

          <div style={{ display: 'flex', gap: '0.25rem', alignItems: 'center' }}>
            <button className="btn btn-ghost btn-sm" onClick={() => setEditing(dc)} style={{ padding: '0.25rem' }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"></path>
                <path d="m15 5 4 4"></path>
              </svg>
            </button>

            <button className="btn btn-ghost btn-sm" onClick={() => remove.mutate(dc.id)}>
              <Trash2 size={12} />
            </button>

            <input type="checkbox" checked={selectedIds.has(dc.id)} onChange={() => toggleSelect(dc.id)}
              style={{ width: 'auto', cursor: 'pointer' }} />
          </div>
        </div>
      ))}

      {editing && (
        <EditCardModal
          cardEntry={editing}
          deckId={deckId}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  )
}

export default function DeckDetail() {
  const { id } = useParams()
  const [showAdd, setShowAdd] = useState(false)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const qc = useQueryClient()
  const [confirmAction, setConfirmAction] = useState(null)

  const toggleSelect = (cardId) => setSelectedIds(prev => {
    const next = new Set(prev)
    if (next.has(cardId)) next.delete(cardId); else next.add(cardId)
    return next
  })

  const bulkRemove = useMutation({
    mutationFn: (ids) => Promise.all([...ids].map(cardId => api.delete(`/decks/${id}/cards/${cardId}`))),
    onSuccess: () => { qc.invalidateQueries(['deck', id]); setSelectedIds(new Set()) },
  })

  const { data: deck, isLoading } = useQuery({
    queryKey: ['deck', id],
    queryFn: () => api.get(`/decks/${id}`).then(r => r.data),
    enabled: !!id && id !== 'undefined',
    retry: false,
    refetchOnWindowFocus: false,
  })

  useEffect(() => {
    document.title = deck ? `${deck.name} - OpenMTG` : 'Decks - OpenMTG'
  }, [deck])

  if (!id || id === 'undefined') return null
  if (isLoading) return <div className="loading">Loading deck…</div>
  if (!deck) return <div className="empty-state"><p>Deck not found.</p></div>

  const commander = deck.cards.filter(c => c.is_commander)
  const mainboard = deck.cards.filter(c => !c.is_sideboard && !c.is_commander)
  const sideboard = deck.cards.filter(c => c.is_sideboard)
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
          <button className="btn btn-ghost btn-sm" onClick={() => downloadFile(`/export/deck/${id}/moxfield`, 'deck.moxfield')}>
          <Download size={15} /> Moxfield
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => downloadFile(`/export/deck/${id}/json`, 'deck.json')}>
          <Download size={15} /> JSON
          </button>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
            <Plus size={18} /> Add Card
          </button>
        </div>
      </div>

      {selectedIds.size > 0 && (
        <div className="deck-card-entry">
          <span style={{ fontSize: '0.875rem' }}>{selectedIds.size} selected</span>
          <button className="btn btn-danger btn-sm"
            onClick={() => setConfirmAction({
              message: `Remove ${selectedIds.size} card(s)?`,
              onConfirm: () => { bulkRemove.mutate(selectedIds); setConfirmAction(null); }
            })}
            disabled={bulkRemove.isPending}>
            <Trash2 size={14} /> {bulkRemove.isPending ? 'Removing…' : 'Remove Selected'}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setSelectedIds(new Set())}>Clear</button>
        </div>
      )}

      <CardSection title="Commander" cards={commander} deckId={id} selectedIds={selectedIds} toggleSelect={toggleSelect} />
      <CardSection title="Mainboard" cards={mainboard} deckId={id} selectedIds={selectedIds} toggleSelect={toggleSelect} />
      <CardSection title="Sideboard" cards={sideboard} deckId={id} selectedIds={selectedIds} toggleSelect={toggleSelect} />

      {deck.cards.length === 0 && (
        <div className="empty-state">
          <p>No cards yet. Add some!</p>
        </div>
      )}

      {showAdd && <AddCardModal deckId={id} onClose={() => setShowAdd(false)} />}
      {confirmAction && (
        <ConfirmModal
          message={confirmAction.message}
          onConfirm={confirmAction.onConfirm}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>
  )
}

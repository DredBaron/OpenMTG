import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Download, BarChart2, LayoutGrid, List, Eye, Pencil } from 'lucide-react'
import { downloadFile } from '../utils/downloadFile'
import api from '../api'
import ConfirmModal from '../components/ConfirmModal'
import CardImageModal from '../components/CardImageModal'
import DeckAnalysisModal from '../components/DeckAnalysisModal'
import DeckAddCardModal from '../components/DeckAddCardModal'

const ZONES = ['Mainboard', 'Sideboard', 'Commander']

function scryfallImg(scryfallId, size = 'normal') {
  if (!scryfallId) return null
  return `https://cards.scryfall.io/${size}/front/${scryfallId[0]}/${scryfallId[1]}/${scryfallId}.jpg`
}

function EditCardModal({ cardEntry, deckId, onClose }) {
  const qc = useQueryClient()
  const card = cardEntry.card

  const initZone = () => {
    if (cardEntry.is_commander) return 'Commander'
    if (cardEntry.is_sideboard) return 'Sideboard'
    return 'Mainboard'
  }

  const [zone, setZone] = useState(initZone)
  const [quantity, setQuantity] = useState(cardEntry.quantity)

  const save = useMutation({
    mutationFn: () => api.patch(`/decks/${deckId}/cards/${cardEntry.id}`, {
      quantity,
      is_commander: zone === 'Commander',
      is_sideboard: zone === 'Sideboard',
    }),
    onSuccess: () => { qc.invalidateQueries(['deck', deckId]); onClose() }
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
        <h2>Edit Card</h2>

        <div className="card-preview-block card-preview-top">
          <div className="card-img-preview">
            {card.scryfall_id &&
              <img src={scryfallImg(card.scryfall_id)} alt={card.name}
                onError={e => { e.currentTarget.style.display = 'none' }} />}
          </div>
          <div className="flex-fill">
            <div className="card-preview-name">{card.name}</div>
            <div className="card-preview-meta">
              {card.set_name ?? card.set_code?.toUpperCase()}
              {card.mana_cost ? ` - ${card.mana_cost}` : ''}
            </div>
            <div className="form-grid-2col mt-sm">
              <div className="form-group">
                <label>Zone</label>
                <select value={zone} onChange={e => setZone(e.target.value)}>
                  {ZONES.map(z => <option key={z} value={z}>{z}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Quantity</label>
                <input type="number" min={1} value={quantity}
                  onChange={e => setQuantity(Math.max(1, parseInt(e.target.value) || 1))} />
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? 'Saving' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

function CardGridItem({ dc, deckId, onEdit, onView }) {
  const [hovered, setHovered] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const qc = useQueryClient()

  const remove = useMutation({
    mutationFn: () => api.delete(`/decks/${deckId}/cards/${dc.id}`),
    onSuccess: () => qc.invalidateQueries(['deck', deckId]),
  })

  const imgSrc = dc.card.image_uri || scryfallImg(dc.card.scryfall_id)

  return (
    <div
      className="deck-grid-item"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { setHovered(false); setConfirmDelete(false) }}>
      {imgSrc && <img src={imgSrc} alt={dc.card.name} />}

      {dc.quantity > 1 && (
        <div className="deck-grid-qty">{dc.quantity}</div>
      )}

      {hovered && (
        <div className="deck-grid-overlay">
          <button className="btn btn-ghost btn-sm btn-block"
            onClick={e => { e.stopPropagation(); onView(dc.card) }}>
            <Eye size={13} /> View
          </button>
          <button className="btn btn-ghost btn-sm btn-block"
            onClick={e => { e.stopPropagation(); onEdit(dc) }}>
            <Pencil size={13} /> Edit
          </button>
          {confirmDelete ? (
            <button className="btn btn-danger btn-sm btn-block"
              onClick={e => { e.stopPropagation(); remove.mutate() }}
              disabled={remove.isPending}>
              <Trash2 size={13} /> Sure?
            </button>
          ) : (
            <button className="btn btn-ghost btn-sm btn-block"
              onClick={e => { e.stopPropagation(); setConfirmDelete(true) }}>
              <Trash2 size={13} /> Delete
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function CardGridSection({ title, cards, deckId, onEdit, onView }) {
  if (!cards || cards.length === 0) return null
  const total = cards.reduce((sum, c) => sum + c.quantity, 0)
  return (
    <div className="deck-section">
      <div className="section-label">{title} ({total})</div>
      <div className="deck-grid">
        {cards.map(dc => (
          <CardGridItem key={dc.id} dc={dc} deckId={deckId} onEdit={onEdit} onView={onView} />
        ))}
      </div>
    </div>
  )
}

function CardSection({ title, cards, deckId, selectedIds, toggleSelect, onView }) {
  const [editing, setEditing] = useState(null)
  const [confirmingDelete, setConfirmingDelete] = useState(new Set())
  const qc = useQueryClient()

  const remove = useMutation({
    mutationFn: (cardId) => api.delete(`/decks/${deckId}/cards/${cardId}`),
    onSuccess: () => qc.invalidateQueries(['deck', deckId]),
  })

  const requestDelete = (cardId) =>
    setConfirmingDelete(prev => new Set(prev).add(cardId))

  const cancelDelete = (cardId) =>
    setConfirmingDelete(prev => {
      const next = new Set(prev); next.delete(cardId); return next
    })

  if (!cards || cards.length === 0) return null

  const total = cards.reduce((sum, c) => sum + c.quantity, 0)
  const allSelected = cards.length > 0 && cards.every(c => selectedIds.has(c.id))
  const toggleAll = () => cards.forEach(c => {
    if (allSelected !== selectedIds.has(c.id)) return
    toggleSelect(c.id)
  })

  return (
    <div className="deck-section">
      <div className="deck-section-header">
        <span>{title} ({total})</span>
        <input className="input-check" type="checkbox" checked={allSelected}
          onChange={toggleAll} title="Select all in section" />
      </div>

      {cards.map(dc => (
        <div key={dc.id} className="deck-card-row">
          <span className="deck-card-qty">{dc.quantity}</span>
          <span className="deck-card-name">{dc.card.name}</span>
          <span className="deck-card-mana">{dc.card.mana_cost}</span>
          {dc.card.price_usd && (
            <span className="deck-card-price">${dc.card.price_usd}</span>
          )}
          <div className="btn-group">
            <button className="btn btn-ghost btn-sm btn-icon"
              onClick={() => onView(dc.card)} title="View card">
              <Eye size={13} />
            </button>
            <button className="btn btn-ghost btn-sm btn-icon" onClick={() => setEditing(dc)}>
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" strokeWidth="2"
                strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z" />
                <path d="m15 5 4 4" />
              </svg>
            </button>
            {confirmingDelete.has(dc.id) ? (
              <button className="btn btn-danger btn-sm btn-icon"
                onClick={() => { remove.mutate(dc.id); cancelDelete(dc.id) }}
                onBlur={() => cancelDelete(dc.id)}>
                <Trash2 size={12} />
              </button>
            ) : (
              <button className="btn btn-ghost btn-sm btn-icon"
                onClick={() => requestDelete(dc.id)}>
                <Trash2 size={12} />
              </button>
            )}
            <input className="input-check" type="checkbox"
              checked={selectedIds.has(dc.id)} onChange={() => toggleSelect(dc.id)} />
          </div>
        </div>
      ))}

      {editing && (
        <EditCardModal cardEntry={editing} deckId={deckId} onClose={() => setEditing(null)} />
      )}
    </div>
  )
}

export default function DeckDetail() {
  const { id } = useParams()
  const [viewMode, setViewMode] = useState('grid')
  const [showAdd, setShowAdd] = useState(false)
  const [showAnalysis, setShowAnalysis] = useState(false)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [editingCard, setEditingCard] = useState(null)
  const [viewingCard, setViewingCard] = useState(null)
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
  if (isLoading) return <div className="loading">Loading deck</div>
  if (!deck) return <div className="empty-state"><p>Deck not found.</p></div>

  const commander = deck.cards.filter(c => c.is_commander)
  const mainboard = deck.cards.filter(c => !c.is_sideboard && !c.is_commander)
  const sideboard = deck.cards.filter(c => c.is_sideboard)
  const totalCards = mainboard.reduce((s, c) => s + c.quantity, 0)
  const totalValue = deck.cards.reduce((s, c) => s + (c.card.price_usd || 0) * c.quantity, 0)

  const gridProps = { deckId: id, onEdit: setEditingCard, onView: setViewingCard }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{deck.name}</h1>
          <div className="page-subtitle">
            {deck.format && <span className="text-capitalize">{deck.format} | </span>}
            {totalCards} cards | Est. <span className="text-gold">${totalValue.toFixed(2)}</span>
          </div>
        </div>

        <div className="flex-gap">
          <div className="btn-group">
            <button
              className={`btn btn-sm ${viewMode === 'grid' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setViewMode('grid')} title="Grid view">
              <LayoutGrid size={15} />
            </button>
            <button
              className={`btn btn-sm ${viewMode === 'list' ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setViewMode('list')} title="List view">
              <List size={15} />
            </button>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowAnalysis(true)}
            disabled={deck.cards.length === 0}>
            <BarChart2 size={15} /> Analyze
          </button>
          <button className="btn btn-ghost btn-sm"
            onClick={() => downloadFile(`/export/deck/${id}/moxfield`, 'deck.moxfield')}>
            <Download size={15} /> Moxfield
          </button>
          <button className="btn btn-ghost btn-sm"
            onClick={() => downloadFile(`/export/deck/${id}/json`, 'deck.json')}>
            <Download size={15} /> JSON
          </button>
          <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
            <Plus size={18} /> Add Card
          </button>
        </div>
      </div>

      {viewMode === 'list' && selectedIds.size > 0 && (
        <div className="deck-card-entry">
          <span className="text-sm">{selectedIds.size} selected</span>
          <button className="btn btn-danger btn-sm"
            onClick={() => setConfirmAction({
              message: `Remove ${selectedIds.size} card(s)?`,
              onConfirm: () => { bulkRemove.mutate(selectedIds); setConfirmAction(null) }
            })}
            disabled={bulkRemove.isPending}>
            <Trash2 size={14} /> {bulkRemove.isPending ? 'Removing' : 'Remove Selected'}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setSelectedIds(new Set())}>Clear</button>
        </div>
      )}

      {viewMode === 'grid' ? (
        <>
          <CardGridSection title="Commander" cards={commander} {...gridProps} />
          <CardGridSection title="Mainboard" cards={mainboard} {...gridProps} />
          <CardGridSection title="Sideboard" cards={sideboard} {...gridProps} />
        </>
      ) : (
        <>
          <CardSection title="Commander" cards={commander} deckId={id}
            selectedIds={selectedIds} toggleSelect={toggleSelect} onView={setViewingCard} />
          <CardSection title="Mainboard" cards={mainboard} deckId={id}
            selectedIds={selectedIds} toggleSelect={toggleSelect} onView={setViewingCard} />
          <CardSection title="Sideboard" cards={sideboard} deckId={id}
            selectedIds={selectedIds} toggleSelect={toggleSelect} onView={setViewingCard} />
        </>
      )}

      {deck.cards.length === 0 && (
        <div className="empty-state"><p>No cards</p></div>
      )}

      {showAdd && <DeckAddCardModal deckId={id} onClose={() => setShowAdd(false)} />}

      {showAnalysis && (
        <DeckAnalysisModal deck={deck} onClose={() => setShowAnalysis(false)} />
      )}

      {editingCard && (
        <EditCardModal cardEntry={editingCard} deckId={id} onClose={() => setEditingCard(null)} />
      )}

      {viewingCard && (
        <CardImageModal card={viewingCard} onClose={() => setViewingCard(null)} />
      )}

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

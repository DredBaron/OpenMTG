import { useState, useEffect } from 'react'
import { useParams, Navigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Eye, Layers, Trash2 } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { usePersistedView } from '../hooks/usePersistedView'
import { DeckPreviewRow } from '../components/DeckPreviewRow'
import CardImageModal from '../components/CardImageModal'
import api from '../api'

const SIZE_MAP = { sm: 60, md: 80, lg: 100 }
const GRID_MAP = { sm: 100, md: 140, lg: 180 }

function ShowroomCardItem({ card, onRemove }) {
  const [hovered, setHovered] = useState(false)
  const [confirmRemove, setConfirmRemove] = useState(false)
  const [viewing, setViewing] = useState(false)

  return (
    <>
      <div
        className="deck-grid-item"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => { setHovered(false); setConfirmRemove(false) }}>
        {card.image_uri && <img src={card.image_uri} alt={card.name} />}
        {!card.image_uri && <div className="showroom-card-placeholder">{card.name}</div>}
        {card.foil && <div className="deck-grid-qty">F</div>}

        {hovered && (
          <div className="deck-grid-overlay">
            <button className="btn btn-ghost btn-sm btn-block"
              onClick={e => { e.stopPropagation(); setViewing(true) }}>
              <Eye size={13} /> View
            </button>
            {confirmRemove ? (
              <button className="btn btn-danger btn-sm btn-block"
                onClick={e => { e.stopPropagation(); onRemove() }}>
                <Trash2 size={13} /> Sure?
              </button>
            ) : (
              <button className="btn btn-ghost btn-sm btn-block"
                onClick={e => { e.stopPropagation(); setConfirmRemove(true) }}>
                <Trash2 size={13} /> Remove
              </button>
            )}
          </div>
        )}
      </div>

      {viewing && <CardImageModal card={card} onClose={() => setViewing(false)} />}
    </>
  )
}

export default function ShowroomEdit() {
  const { username } = useParams()
  const { user, showroomEnabled } = useAuth()
  const slug = username.toLowerCase()
  const qc = useQueryClient()
  const [cardSize, setCardSize] = usePersistedView('showroom-card-size', 'md')
  const cardW = SIZE_MAP[cardSize]
  const gridMin = GRID_MAP[cardSize]

  const { data, isLoading } = useQuery({
    queryKey: ['showroom', slug],
    queryFn: () => api.get(`/showroom/display/${slug}`).then(r => r.data),
  })

  const removeCard = useMutation({
    mutationFn: (id) => api.patch(`/collection/${id}`, { in_showroom: false }),
    onSuccess: () => qc.invalidateQueries(['showroom', slug]),
  })

  const removeDeck = useMutation({
    mutationFn: (id) => api.patch(`/decks/${id}`, { is_public: false }),
    onSuccess: () => qc.invalidateQueries(['showroom', slug]),
  })

  useEffect(() => {
    document.title = 'Showroom - OpenMTG'
  }, [])

  if (!showroomEnabled) {
    return <Navigate to="/collection" replace />
  }

  if (user && user.username.toLowerCase() !== slug) {
    return <Navigate to={`/showroom/display/${slug}`} replace />
  }

  const decks = data?.decks ?? []
  const cards = data?.cards ?? []
  const hasContent = decks.length > 0 || cards.length > 0

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Showroom</h1>
          <p className="page-subtitle">Choose which decks and cards appear on your public display.</p>
        </div>
        <div className="flex-gap">
          <div className="btn-group">
            {['sm', 'md', 'lg'].map(s => (
              <button
                key={s}
                className={`btn btn-sm ${cardSize === s ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setCardSize(s)}>
                {s.toUpperCase()}
              </button>
            ))}
          </div>
          <Link
            to={`/showroom/display/${slug}`}
            className="btn btn-ghost btn-sm"
            target="_blank"
            rel="noreferrer">
            <Eye size={14} /> View Display
          </Link>
        </div>
      </div>

      {isLoading && <div className="loading">Loading showroom</div>}

      {!isLoading && !hasContent && (
        <div className="empty-state">
          <Eye size={32} />
          <p>Nothing on display yet.</p>
          <p>Toggle visibility from the Decks and Collection pages.</p>
        </div>
      )}

      {!isLoading && decks.length > 0 && (
        <div className="showroom-section">
          <div className="deck-section-header">
            <span className="showroom-section-label"><Layers size={15} /> Decks</span>
          </div>
          <div className="deck-list">
            {decks.map(deck => (
              <DeckPreviewRow
                key={deck.id}
                deck={deck}
                cardW={cardW}
                actions={
                  <button
                    className="btn btn-ghost btn-sm"
                    title="Remove from showroom"
                    style={{ color: 'var(--accent)' }}
                    onClick={() => removeDeck.mutate(deck.id)}>
                    <Eye size={14} />
                  </button>
                }
              />
            ))}
          </div>
        </div>
      )}

      {!isLoading && cards.length > 0 && (
        <div className="showroom-section">
          <div className="deck-section-header">
            <span className="showroom-section-label">Cards</span>
          </div>
          <div className="deck-grid" style={{ gridTemplateColumns: `repeat(auto-fill, minmax(${gridMin}px, 1fr))` }}>
            {cards.map(card => (
              <ShowroomCardItem
                key={card.id}
                card={card}
                onRemove={() => removeCard.mutate(card.id)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

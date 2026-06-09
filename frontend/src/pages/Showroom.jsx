import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Eye } from 'lucide-react'
import { usePersistedView } from '../hooks/usePersistedView'
import api from '../api'

const CARD_GAP = 4
const SIZE_MAP = { sm: 60, md: 80, lg: 100 }
const GRID_MAP = { sm: 100, md: 140, lg: 180 }

function scryfallImg(scryfallId, size = 'small') {
  if (!scryfallId) return null
  return `https://cards.scryfall.io/${size}/front/${scryfallId[0]}/${scryfallId[1]}/${scryfallId}.jpg`
}

function DeckRow({ deck, cardW }) {
  const stripRef = useRef(null)
  const [visibleCount, setVisibleCount] = useState(0)

  useEffect(() => {
    if (!stripRef.current) return
    const calc = (w) => Math.max(0, Math.floor((w + CARD_GAP) / (cardW + CARD_GAP)))
    setVisibleCount(calc(stripRef.current.getBoundingClientRect().width))
    const obs = new ResizeObserver(([entry]) => setVisibleCount(calc(entry.contentRect.width)))
    obs.observe(stripRef.current)
    return () => obs.disconnect()
  }, [cardW])

  const visible = deck.preview_cards.slice(0, visibleCount)

  return (
    <div className="deck-column showroom-deck-row">
      <div className="showroom-deck-info">
        <div className="deck-column-name">{deck.name}</div>
        <div className="deck-column-meta">
          {deck.format && <span className="text-capitalize">{deck.format}</span>}
          {deck.description && ` | ${deck.description}`}
        </div>
        {deck.card_count > 0 && (
          <div className="deck-column-meta">{deck.card_count} cards</div>
        )}
      </div>
      <div ref={stripRef} className="showroom-deck-strip">
        {visible.map((c, i) => (
          <img
            key={i}
            src={scryfallImg(c.scryfall_id)}
            alt=""
            style={{ width: cardW }}
            className={`showroom-deck-strip-img${c.is_commander ? ' showroom-commander' : ''}`}
            onError={e => { e.currentTarget.style.display = 'none' }}
          />
        ))}
      </div>
    </div>
  )
}

export default function Showroom() {
  const { username } = useParams()
  const slug = username.toLowerCase()
  const [cardSize, setCardSize] = usePersistedView('showroom-card-size', 'md')
  const cardW = SIZE_MAP[cardSize]
  const gridMin = GRID_MAP[cardSize]

  useEffect(() => {
    document.title = `${slug}'s Showroom - OpenMTG`
  }, [slug])

  const { data, isLoading, isError } = useQuery({
    queryKey: ['showroom', slug],
    queryFn: () => api.get(`/showroom/display/${slug}`).then(r => r.data),
  })

  const decks = data?.decks ?? []
  const cards = data?.cards ?? []
  const hasContent = decks.length > 0 || cards.length > 0

  return (
    <div className="showroom-page">
      <div className="showroom-header">
        <div className="showroom-header-left">
          <span className="logo">OpenMTG</span>
          <span className="showroom-owner">{slug}'s Showroom</span>
        </div>
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
      </div>

      {isLoading && <div className="loading">Loading showroom</div>}

      {isError && (
        <div className="empty-state">
          <Eye size={32} />
          <p>Showroom not found.</p>
        </div>
      )}

      {!isLoading && !isError && !hasContent && (
        <div className="empty-state">
          <Eye size={32} />
          <p>Nothing on display yet.</p>
        </div>
      )}

      {!isLoading && !isError && decks.length > 0 && (
        <div className="showroom-section">
          <div className="deck-section-header">
            <span className="showroom-section-label">Decks</span>
          </div>
          <div className="deck-list">
            {decks.map(deck => (
              <DeckRow key={deck.id} deck={deck} cardW={cardW} />
            ))}
          </div>
        </div>
      )}

      {!isLoading && !isError && cards.length > 0 && (
        <div className="showroom-section">
          <div className="deck-section-header">
            <span className="showroom-section-label">Cards</span>
          </div>
          <div className="deck-grid" style={{ gridTemplateColumns: `repeat(auto-fill, minmax(${gridMin}px, 1fr))` }}>
            {cards.map(card => (
              <div key={card.id} className="deck-grid-item">
                {card.image_uri
                  ? <img src={card.image_uri} alt={card.name} />
                  : <div className="showroom-card-placeholder">{card.name}</div>
                }
                {card.foil && <div className="deck-grid-qty">F</div>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

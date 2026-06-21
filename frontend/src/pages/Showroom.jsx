import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Eye } from 'lucide-react'
import { usePersistedView } from '../hooks/usePersistedView'
import { DeckPreviewRow } from '../components/DeckPreviewRow'
import CardImageModal from '../components/CardImageModal'
import api from '../api'

const SIZE_MAP = { sm: 60, md: 80, lg: 100 }
const GRID_MAP = { sm: 100, md: 140, lg: 180 }

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

  const [viewing, setViewing] = useState(null)

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
              <DeckPreviewRow
                key={deck.id}
                deck={deck}
                cardW={cardW}
                actions={
                  <Link
                    to={`/showroom/display/${slug}/deck/${deck.id}`}
                    className="btn btn-ghost btn-sm">
                    View
                  </Link>
                }
              />
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
              <div
                key={card.id}
                className="deck-grid-item showroom-card-clickable"
                onClick={() => setViewing(card)}>
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

      {viewing && <CardImageModal card={viewing} onClose={() => setViewing(null)} />}
    </div>
  )
}

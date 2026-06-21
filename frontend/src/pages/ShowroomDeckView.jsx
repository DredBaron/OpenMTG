import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft } from 'lucide-react'
import CardImageModal from '../components/CardImageModal'
import api from '../api'

function CardSection({ title, entries, gridMin }) {
  const [viewing, setViewing] = useState(null)
  if (!entries.length) return null

  return (
    <div className="showroom-section">
      <div className="deck-section-header">
        <span className="showroom-section-label">{title}</span>
        <span className="deck-section-count">{entries.reduce((s, dc) => s + dc.quantity, 0)} cards</span>
      </div>
      <div className="deck-grid" style={{ gridTemplateColumns: `repeat(auto-fill, minmax(${gridMin}px, 1fr))` }}>
        {entries.map(dc => (
          <div
            key={dc.id}
            className="deck-grid-item showroom-card-clickable"
            onClick={() => setViewing(dc.card)}>
            {dc.card.image_uri
              ? <img src={dc.card.image_uri} alt={dc.card.name} />
              : <div className="showroom-card-placeholder">{dc.card.name}</div>
            }
            {dc.quantity > 1 && <div className="deck-grid-qty">{dc.quantity}</div>}
          </div>
        ))}
      </div>
      {viewing && <CardImageModal card={viewing} onClose={() => setViewing(null)} />}
    </div>
  )
}

export default function ShowroomDeckView() {
  const { username, deckId } = useParams()
  const slug = username.toLowerCase()

  const { data: deck, isLoading, isError } = useQuery({
    queryKey: ['showroom-deck', slug, deckId],
    queryFn: () => api.get(`/showroom/display/${slug}/deck/${deckId}`).then(r => r.data),
  })

  useEffect(() => {
    if (deck) document.title = `${deck.name} - OpenMTG`
  }, [deck])

  if (isLoading) return <div className="showroom-page"><div className="loading">Loading deck</div></div>

  if (isError) return (
    <div className="showroom-page">
      <div className="showroom-header">
        <span className="logo">OpenMTG</span>
      </div>
      <div className="empty-state">
        <p>Deck not found.</p>
        <Link to={`/showroom/display/${slug}`} className="btn btn-ghost">Back to Showroom</Link>
      </div>
    </div>
  )

  const commanders = deck.cards.filter(dc => dc.is_commander)
  const mainboard  = deck.cards.filter(dc => !dc.is_commander && !dc.is_sideboard)
  const sideboard  = deck.cards.filter(dc => dc.is_sideboard)

  return (
    <div className="showroom-page">
      <div className="showroom-header">
        <div className="showroom-header-left">
          <span className="logo">OpenMTG</span>
          <Link to={`/showroom/display/${slug}`} className="btn btn-ghost btn-sm">
            <ChevronLeft size={14} /> {slug}'s Showroom
          </Link>
        </div>
      </div>

      <div className="showroom-deck-view-header">
        <h2 className="showroom-deck-view-title">{deck.name}</h2>
        <div className="deck-column-meta">
          {deck.format && <span className="text-capitalize">{deck.format}</span>}
          {deck.description && ` · ${deck.description}`}
        </div>
      </div>

      <CardSection title="Commander" entries={commanders} gridMin={180} />
      <CardSection title="Main Deck" entries={mainboard}  gridMin={140} />
      <CardSection title="Sideboard" entries={sideboard}  gridMin={140} />
    </div>
  )
}

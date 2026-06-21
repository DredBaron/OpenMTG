import { useEffect, useRef, useState } from 'react'

const CARD_GAP = 4

function scryfallImg(scryfallId, size = 'small') {
  if (!scryfallId) return null
  return `https://cards.scryfall.io/${size}/front/${scryfallId[0]}/${scryfallId[1]}/${scryfallId}.jpg`
}

export function DeckPreviewRow({ deck, cardW, actions }) {
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

  const visible = (deck.preview_cards ?? []).slice(0, visibleCount)

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
      {actions && <div className="deck-preview-actions">{actions}</div>}
    </div>
  )
}

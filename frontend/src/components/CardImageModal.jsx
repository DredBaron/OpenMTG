export default function CardImageModal({ card, onClose }) {
  const largeImage = card.image_uri ? card.image_uri.replace('/normal/', '/large/') : null
  const scryfallUrl = `https://scryfall.com/search?q=${encodeURIComponent(card.name)}`

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div onClick={e => e.stopPropagation()}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
        {largeImage && (
          <img src={largeImage} alt={card.name}
            style={{
              borderRadius: 16,
              maxWidth: '90vw',
              maxHeight: '80vh',
              boxShadow: '0 8px 32px rgba(0,0,0,0.6)'
            }} />
        )}
        <a href={scryfallUrl} target="_blank" rel="noreferrer"
          className="btn btn-primary"
          style={{ textDecoration: 'none' }}>
          View Rulings on Scryfall
        </a>
      </div>
    </div>
  )
}

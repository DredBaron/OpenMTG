export default function CardImageModal({ card, onClose }) {
  const largeImage = card.image_uri ? card.image_uri.replace('/normal/', '/large/') : null
  const scryfallUrl = `https://scryfall.com/search?q=${encodeURIComponent(card.name)}`

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="card-viewer" onClick={e => e.stopPropagation()}>
        {largeImage && (
          <img src={largeImage} alt={card.name} className="card-viewer-img" />
        )}
        <a href={scryfallUrl} target="_blank" rel="noreferrer"
          className="btn btn-primary">
          View Rulings on Scryfall
        </a>
      </div>
    </div>
  )
}

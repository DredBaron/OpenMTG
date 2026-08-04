import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import api from '../api'

function usePhotoBlob(entryId, side, tradeId) {
  const [src, setSrc] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!entryId || !side) return
    let current = true
    let objectUrl = null

    setLoading(true)
    setSrc(null)

    const url = tradeId
      ? `/trades/${tradeId}/photos/${entryId}/${side}`
      : `/collection/${entryId}/photos/${side}`

    api.get(url, { responseType: 'blob' })
      .then(r => {
        if (!current) return
        objectUrl = URL.createObjectURL(r.data)
        setSrc(objectUrl)
      })
      .catch(() => { if (current) setSrc(null) })
      .finally(() => { if (current) setLoading(false) })

    return () => {
      current = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [entryId, side, tradeId])

  return { src, loading }
}

export default function CardPhotoViewer({ entryId, cardName, photos, tradeId, onClose }) {
  const availableSides = photos.map(p => p.side)
  const [activeSide, setActiveSide] = useState(availableSides[0] || 'front')
  const { src, loading } = usePhotoBlob(entryId, activeSide, tradeId)

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 380 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h2 style={{ margin: 0, fontSize: '1rem' }}>{cardName}</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        {availableSides.length > 1 && (
          <div className="flex-gap" style={{ marginBottom: '0.75rem' }}>
            {availableSides.map(s => (
              <button key={s} className={`btn btn-sm ${activeSide === s ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => setActiveSide(s)}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        )}

        <div className="photo-viewer-frame">
          {loading && <div className="loading" style={{ minHeight: 200 }}>Loading</div>}
          {!loading && src && <img src={src} alt={`${cardName} ${activeSide}`} className="photo-viewer-img" />}
          {!loading && !src && <div className="empty-state" style={{ minHeight: 200 }}>Photo unavailable</div>}
        </div>

      </div>
    </div>
  )
}

import { useState, useRef, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Upload, ImagePlus } from 'lucide-react'
import api from '../api'
import { MAX_PHOTO_BYTES, PHOTO_TYPES } from '../constants'

const MAX_PHOTO_MB = MAX_PHOTO_BYTES / (1024 * 1024)
const TOO_LARGE = `Photos can be at most ${MAX_PHOTO_MB} MB.`
const WRONG_TYPE = 'Photos must be JPEG, PNG or WebP images.'

function uploadErrorMessage(err) {
  // nginx answers 413 with an HTML page, so don't rely on a JSON detail for it.
  if (err.response?.status === 413) return TOO_LARGE
  const detail = err.response?.data?.detail
  return typeof detail === 'string' ? detail : 'Upload failed. Please try again.'
}

export default function PhotoUploadModal({ entryId, initialSide = 'front', onClose }) {
  const qc = useQueryClient()
  const [side, setSide] = useState(initialSide)
  const [file, setFile] = useState(null)
  const [newPreview, setNewPreview] = useState(null)
  const [loadedPhoto, setLoadedPhoto] = useState({ side: null, src: null })
  const [dragging, setDragging] = useState(false)
  const [selectError, setSelectError] = useState('')
  const inputRef = useRef(null)

  useEffect(() => {
    let current = true
    let objectUrl = null

    api.get(`/collection/${entryId}/photos/${side}`, { responseType: 'blob' })
      .then(r => {
        if (!current) return
        objectUrl = URL.createObjectURL(r.data)
        setLoadedPhoto({ side, src: objectUrl })
      })
      .catch(() => { if (current) setLoadedPhoto({ side, src: null }) })

    return () => {
      current = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [entryId, side])

  const existing = loadedPhoto.side === side ? loadedPhoto.src : null

  const handleSideChange = (s) => {
    if (s === side) return
    setFile(null)
    if (newPreview) { URL.revokeObjectURL(newPreview); setNewPreview(null) }
    setSide(s)
  }

  const selectFile = (f) => {
    if (!f) return
    // Checked again by the server, which also verifies the file contents.
    if (!PHOTO_TYPES.includes(f.type)) { setSelectError(WRONG_TYPE); return }
    if (f.size > MAX_PHOTO_BYTES) { setSelectError(TOO_LARGE); return }
    setSelectError('')
    upload.reset()
    if (newPreview) URL.revokeObjectURL(newPreview)
    setFile(f)
    setNewPreview(URL.createObjectURL(f))
  }

  const clearNew = () => {
    if (newPreview) URL.revokeObjectURL(newPreview)
    setFile(null)
    setNewPreview(null)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    selectFile(e.dataTransfer.files[0])
  }

  const upload = useMutation({
    mutationFn: () => {
      const form = new FormData()
      form.append('file', file)
      return api.post(`/collection/${entryId}/photos/${side}`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
    },
    onSuccess: () => {
      qc.invalidateQueries(['collection'])
      onClose()
    },
  })

  const previewSrc = newPreview || existing

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 420 }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0 }}>Card Photo</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose}><X size={16} /></button>
        </div>

        <div className="form-group">
          <label>Side</label>
          <div className="flex-gap">
            {['front', 'back'].map(s => (
              <button key={s} className={`btn btn-sm ${side === s ? 'btn-primary' : 'btn-ghost'}`}
                onClick={() => handleSideChange(s)}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div
          className={`photo-drop-zone${dragging ? ' photo-drop-zone-active' : ''}`}
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
        >
          {previewSrc?.startsWith('blob:') ? (
            <img src={previewSrc} alt={`${side} photo`} className="photo-drop-preview" />
          ) : (
            <div className="photo-drop-hint">
              <ImagePlus size={32} style={{ opacity: 0.4 }} />
              <span>Drag &amp; drop image here</span>
              <span className="text-muted-sm">or click to browse</span>
              <span className="text-muted-sm">JPEG, PNG or WebP, up to {MAX_PHOTO_MB} MB</span>
            </div>
          )}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={PHOTO_TYPES.join(',')}
          style={{ display: 'none' }}
          onChange={e => selectFile(e.target.files[0])}
        />

        {newPreview && (
          <button className="btn btn-ghost btn-sm" style={{ marginTop: '0.5rem' }}
            onClick={clearNew}>
            Clear new selection
          </button>
        )}

        {(selectError || upload.isError) && (
          <div className="error" style={{ marginTop: '0.5rem' }}>
            {selectError || uploadErrorMessage(upload.error)}
          </div>
        )}

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => upload.mutate()}
            disabled={!file || upload.isPending}>
            <Upload size={14} />
            {upload.isPending ? 'Uploading' : 'Upload'}
          </button>
        </div>
      </div>
    </div>
  )
}

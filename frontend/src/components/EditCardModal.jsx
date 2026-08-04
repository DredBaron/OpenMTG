import { useState } from 'react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import { Camera } from 'lucide-react'
import api from '../api'
import SetPicker from './SetPicker'
import { useCurrency } from '../hooks/useCurrency'
import { formatPrice, resolvePrice } from '../utils/currency'
import PhotoUploadModal from './PhotoUploadModal'

export default function EditCardModal({ entry, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    quantity: entry.quantity,
    condition: entry.condition,
    foil: entry.foil,
    language: entry.language,
    notes: entry.notes || '',
    scryfall_id: entry.card.scryfall_id,
    on_loan: entry.on_loan || false,
    loaned_to: entry.loaned_to || '',
    loan_date: entry.loan_date ? entry.loan_date.split('T')[0] : '',
  })
  const [card, setCard] = useState(entry.card)
  const [showPhotos, setShowPhotos] = useState(false)
  const { currency, market } = useCurrency()

  const save = useMutation({
    mutationFn: () => {
      const payload = { ...form }
      if (payload.loan_date === '') payload.loan_date = null
      if (!payload.on_loan) { payload.loaned_to = undefined; payload.loan_date = undefined }
      return api.patch(`/collection/${entry.id}`, payload)
    },
    onSuccess: () => { qc.invalidateQueries(['collection']); onClose() }
  })

  return (
    <>
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Edit: {entry.card.name}</h2>

        <div className="card-preview-block">
          {card.image_uri &&
            <img src={card.image_uri} alt={card.name} className="card-thumb-md" />}
          <div>
            <div className="card-preview-name">{card.name}</div>
            <div className="card-preview-meta">
              {card.set_name} | #{card.collector_number}
            </div>
            {resolvePrice(card, currency, false, market) != null &&
              <div className="text-muted-sm" style={{ color: 'var(--gold)' }}>
                {formatPrice(resolvePrice(card, currency, false, market), currency, market)}
                {resolvePrice(card, currency, true, market) != null &&
                  <span style={{ color: 'var(--foil)', marginLeft: '0.4rem' }}>
                    {formatPrice(resolvePrice(card, currency, true, market), currency, market)} foil
                  </span>}
              </div>}
          </div>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <SetPicker
            card={card}
            onSelect={(printing) => {
              setCard(prev => ({
                ...prev,
                scryfall_id:      printing.scryfall_id,
                set_code:         printing.set_code,
                set_name:         printing.set_name,
                collector_number: printing.collector_number,
                rarity:           printing.rarity,
                image_uri:        printing.image_uri,
                price_usd:        printing.price_usd,
                price_usd_foil:   printing.price_usd_foil,
              }))
              setForm(f => ({ ...f, scryfall_id: printing.scryfall_id }))
            }}
          />
        </div>

        <div className="form-grid-2col">
          <div className="form-group">
            <label>Quantity</label>
            <input type="number" min={1} value={form.quantity}
              onChange={e => setForm(f => ({ ...f, quantity: parseInt(e.target.value) }))} />
          </div>
          <div className="form-group">
            <label>Condition</label>
            <select value={form.condition}
              onChange={e => setForm(f => ({ ...f, condition: e.target.value }))}>
              {['NM','LP','MP','HP','DMG'].map(c => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Language</label>
            <input value={form.language}
              onChange={e => setForm(f => ({ ...f, language: e.target.value }))} />
          </div>
          <div className="form-group" style={{ justifyContent: 'flex-end' }}>
            <label className="checkbox-label">
              <input type="checkbox" checked={form.foil}
                onChange={e => setForm(f => ({ ...f, foil: e.target.checked }))}
                style={{ width: 'auto' }} />
              Foil
            </label>
          </div>
        </div>

        <div className="form-group">
          <label>Notes</label>
          <textarea rows={2} value={form.notes}
            onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
        </div>

        <div className="form-group">
          <label>Card Photos</label>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowPhotos(true)}>
            <Camera size={14} /> Photos
          </button>
        </div>

        <div className="form-group">
          <label className="checkbox-label">
            <input type="checkbox" checked={form.on_loan}
              onChange={e => setForm(f => ({ ...f, on_loan: e.target.checked }))}
              style={{ width: 'auto' }} />
            On Loan
          </label>
        </div>

        {form.on_loan && (
          <div className="form-grid-2col">
            <div className="form-group">
              <label>Loaned To</label>
              <input value={form.loaned_to}
                placeholder="Name or note"
                onChange={e => setForm(f => ({ ...f, loaned_to: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>Loan Date</label>
              <input type="date" value={form.loan_date}
                onChange={e => setForm(f => ({ ...f, loan_date: e.target.value }))} />
            </div>
          </div>
        )}

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => save.mutate()}
            disabled={save.isPending}>
            {save.isPending ? 'Saving' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>

    {showPhotos && (
      <PhotoUploadModal
        entryId={entry.id}
        initialSide="front"
        onClose={() => setShowPhotos(false)}
      />
    )}
    </>
  )
}

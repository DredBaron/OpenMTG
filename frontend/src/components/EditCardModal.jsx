import { useState } from 'react'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import api from '../api'
import SetPicker from './SetPicker'
import { useAuth } from '../hooks/useAuth'
import { formatPrice, resolvePrice } from '../utils/currency'

export default function EditCardModal({ entry, onClose }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    quantity: entry.quantity,
    condition: entry.condition,
    foil: entry.foil,
    language: entry.language,
    notes: entry.notes || '',
    scryfall_id: entry.card.scryfall_id,
  })
  const [card, setCard] = useState(entry.card)
  const { user } = useAuth()
  const currency = user?.preferred_currency || 'usd'

  const save = useMutation({
    mutationFn: () => api.patch(`/collection/${entry.id}`, form),
    onSuccess: () => { qc.invalidateQueries(['collection']); onClose() }
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Edit: {entry.card.name}</h2>

        <div className="card-preview-block">
          {card.image_uri &&
            <img src={card.image_uri} alt={card.name}
              style={{ width: 48, borderRadius: 4, flexShrink: 0 }} />}
          <div>
            <div style={{ fontWeight: 600 }}>{card.name}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {card.set_name} · #{card.collector_number}
            </div>
            {resolvePrice(card, currency) != null &&
              <div style={{ fontSize: '0.8rem', color: 'var(--gold)' }}>
                {formatPrice(resolvePrice(card, currency), currency)}
                {resolvePrice(card, currency, true) != null &&
                  <span style={{ color: 'var(--foil)', marginLeft: '0.4rem' }}>
                    {formatPrice(resolvePrice(card, currency, true), currency)} foil
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
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
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

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={() => save.mutate()}
            disabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  )
}

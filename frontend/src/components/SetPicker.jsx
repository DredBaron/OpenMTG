import { useState, useEffect, useRef } from 'react'
import api from '../api'

export default function SetPicker({ card, onSelect }) {
  const [printings, setPrintings] = useState([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState(null)
  const dropdownRef = useRef(null)

  useEffect(() => {
    setLoading(true)
    api.get(`/cards/${card.scryfall_id}/printings`)
      .then(res => {
        setPrintings(res.data)
        const current = res.data.find(p => p.scryfall_id === card.scryfall_id)
        setSelected(current || res.data[0] || null)
      })
      .finally(() => setLoading(false))
  }, [card.scryfall_id])

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const choose = (printing) => {
    setSelected(printing)
    setOpen(false)
    onSelect(printing)
  }

  if (loading) return (
    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '0.5rem 0' }}>
      Loading printings…
    </div>
  )

  if (!selected) return null

  return (
    <div style={{ position: 'relative' }} ref={dropdownRef}>
      <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)',
        display: 'block', marginBottom: '0.4rem' }}>
        Set / Printing
      </label>

      {/* Trigger button */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', background: 'var(--bg)', border: '1px solid var(--border)',
          borderRadius: 'var(--radius)', padding: '0.6rem 0.75rem', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: '0.6rem',
          color: 'var(--text)', textAlign: 'left', transition: 'border-color 0.15s',
          ...(open ? { borderColor: 'var(--accent)' } : {})
        }}>
        <SetIcon setCode={selected.set_code} size={20} />
        <span style={{ flex: 1, fontSize: '0.875rem' }}>
          {selected.set_name}
          <span style={{ color: 'var(--text-muted)', marginLeft: '0.4rem' }}>
            #{selected.collector_number}
          </span>
        </span>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
          {selected.released_at?.slice(0, 4)}
        </span>
        {selected.price_usd &&
          <span style={{ color: 'var(--gold)', fontWeight: 600, fontSize: '0.85rem' }}>
            ${selected.price_usd}
          </span>}
        <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem',
          transform: open ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
          ▼
        </span>
      </button>

      {/* Dropdown list */}
      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 200,
          background: 'var(--surface)', border: '1px solid var(--accent)',
          borderRadius: 'var(--radius)', maxHeight: 320, overflowY: 'auto',
          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
        }}>
          {printings.map(printing => (
            <div
              key={printing.scryfall_id}
              onClick={() => choose(printing)}
              style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem',
                padding: '0.65rem 0.75rem', cursor: 'pointer',
                borderBottom: '1px solid var(--border)',
                background: printing.scryfall_id === selected.scryfall_id
                  ? 'var(--surface2)' : 'transparent',
                transition: 'background 0.1s',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--surface2)'}
              onMouseLeave={e => {
                e.currentTarget.style.background =
                  printing.scryfall_id === selected.scryfall_id
                    ? 'var(--surface2)' : 'transparent'
              }}>
              <SetIcon setCode={printing.set_code} size={22} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: '0.875rem', fontWeight: 500,
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {printing.set_name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  #{printing.collector_number} · {printing.rarity} · {printing.released_at?.slice(0, 4)}
                </div>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                {printing.price_usd
                  ? <div style={{ color: 'var(--gold)', fontWeight: 600, fontSize: '0.85rem' }}>
                      ${printing.price_usd}
                    </div>
                  : <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>—</div>}
                {printing.price_usd_foil &&
                  <div style={{ color: '#c09af0', fontSize: '0.75rem' }}>
                    ${printing.price_usd_foil} foil
                  </div>}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.3rem' }}>
        {printings.length} printing{printings.length !== 1 ? 's' : ''} available
      </div>
    </div>
  )
}

function SetIcon({ setCode, size = 20 }) {
  const [errored, setErrored] = useState(false)
  const url = `https://svgs.scryfall.io/sets/${setCode}.svg`

  if (errored) {
    return (
      <span style={{
        width: size, height: size, display: 'inline-flex', alignItems: 'center',
        justifyContent: 'center', fontSize: '0.6rem', color: 'var(--text-muted)',
        fontWeight: 700, textTransform: 'uppercase', flexShrink: 0,
      }}>
        {setCode}
      </span>
    )
  }

  return (
    <img
      src={url}
      alt={setCode}
      width={size}
      height={size}
      onError={() => setErrored(true)}
      style={{
        flexShrink: 0,
        filter: 'invert(1) sepia(1) saturate(0) brightness(1.5)',
        objectFit: 'contain',
      }}
    />
  )
}

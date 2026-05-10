import { useState, useEffect, useRef, useCallback } from 'react'
import api from '../api'
import { useAuth } from '../hooks/useAuth'
import { formatPrice, resolvePrice } from '../utils/currency'

export default function SetPicker({ card, onSelect }) {
  const [printings, setPrintings] = useState([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [selected, setSelected] = useState(null)
  const [dropdownPos, setDropdownPos] = useState(null)
  const triggerRef = useRef(null)
  const dropdownRef = useRef(null)
  const { user } = useAuth()
  const currency = user?.preferred_currency || 'usd'

  useEffect(() => {
    const fetchPrintings = async () => {
      setLoading(true)
      try {
        const res = await api.get(`/cards/${card.scryfall_id}/printings`)
        setPrintings(res.data)
        const current = res.data.find(p => p.scryfall_id === card.scryfall_id)
        setSelected(current || res.data[0] || null)
      } catch (err) {
        console.error(err)
      } finally {
        setLoading(false)
      }
    }
    fetchPrintings()
  }, [card.scryfall_id])

  useEffect(() => {
    const handler = (e) => {
      if (
        dropdownRef.current && !dropdownRef.current.contains(e.target) &&
        triggerRef.current && !triggerRef.current.contains(e.target)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const openDropdown = useCallback(() => {
    if (!triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    const vh = window.innerHeight
    const gap = 4
    const spaceBelow = vh - rect.bottom - gap
    const spaceAbove = rect.top - gap

    if (spaceBelow >= spaceAbove) {
      setDropdownPos({ top: rect.bottom + gap, left: rect.left, width: rect.width, maxHeight: spaceBelow })
    } else {
      setDropdownPos({ bottom: vh - rect.top + gap, left: rect.left, width: rect.width, maxHeight: spaceAbove })
    }
    setOpen(o => !o)
  }, [])

  const choose = (printing) => {
    setSelected(printing)
    setOpen(false)
    onSelect(printing)
  }

  if (loading) return <div className="set-picker-loading">Loading printings…</div>

  if (!selected) return null

  return (
    <div className="set-picker">
      <label>Set / Printing</label>

      <button
        ref={triggerRef}
        className={`set-picker-trigger${open ? ' open' : ''}`}
        onClick={openDropdown}
      >
        <SetIcon setCode={selected.set_code} />
        <span className="set-picker-trigger-name">
          {selected.set_name}
          <span className="set-picker-trigger-num">#{selected.collector_number}</span>
        </span>
        <span className="set-picker-trigger-year">{selected.released_at?.slice(0, 4)}</span>
        {resolvePrice(selected, currency) != null &&
          <span className="set-picker-trigger-price">
            {formatPrice(resolvePrice(selected, currency), currency)}
          </span>}
        <span className={`set-picker-chevron${open ? ' open' : ''}`}>▼</span>
      </button>

      {open && dropdownPos && (
        <div
          ref={dropdownRef}
          className="set-picker-dropdown"
          style={{
            top: dropdownPos.top ?? undefined,
            bottom: dropdownPos.bottom ?? undefined,
            left: dropdownPos.left,
            width: dropdownPos.width,
            maxHeight: dropdownPos.maxHeight,
          }}
        >
          {printings.map(printing => (
            <div
              key={printing.scryfall_id}
              className={`set-picker-row${printing.scryfall_id === selected.scryfall_id ? ' selected' : ''}`}
              onClick={() => choose(printing)}
            >
              <SetIcon setCode={printing.set_code} />
              <div className="set-picker-row-info">
                <div className="set-picker-row-name">{printing.set_name}</div>
                <div className="set-picker-row-meta">
                  #{printing.collector_number} | {printing.rarity} | {printing.released_at?.slice(0, 4)}
                </div>
              </div>
              <div className="set-picker-row-prices">
                {resolvePrice(printing, currency) != null
                  ? <div className="set-picker-price">
                      {formatPrice(resolvePrice(printing, currency), currency)}
                    </div>
                  : <div className="set-picker-price-none">-</div>}
                {resolvePrice(printing, currency, true) != null &&
                  <div className="set-picker-foil">
                    {formatPrice(resolvePrice(printing, currency, true), currency)} foil
                  </div>}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="set-picker-count">
        {printings.length} printing{printings.length !== 1 ? 's' : ''} available
      </div>
    </div>
  )
}

function SetIcon({ setCode }) {
  const [errored, setErrored] = useState(false)
  const url = `https://svgs.scryfall.io/sets/${setCode}.svg`

  if (errored) {
    return <span className="set-icon-fallback">{setCode}</span>
  }

  return (
    <img
      src={url}
      alt={setCode}
      className="set-icon"
      onError={() => setErrored(true)}
    />
  )
}

import { useState, useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import api from '../api'

const ZONES = ['Mainboard', 'Sideboard', 'Commander']

function scryfallImg(scryfallId, size = 'small') {
    if (!scryfallId) return null
        return `https://cards.scryfall.io/${size}/front/${scryfallId[0]}/${scryfallId[1]}/${scryfallId}.jpg`
}

function CardResult({ card, onClick }) {
    const [imgError, setImgError] = useState(false)

    return (
        <div className="search-result-item" onClick={onClick}>
        <div style={{ width: 36, height: 50, flexShrink: 0, borderRadius: 3,
            background: 'var(--surface2)', overflow: 'hidden',
            display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {!imgError
                ? <img src={scryfallImg(card.scryfall_id, 'small')} alt=""
                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                onError={() => setImgError(true)} />
                : <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)',
                    textAlign: 'center', padding: '0 2px' }}>
                    {card.set_code?.toUpperCase()}
                    </span>
            }
            </div>
            <div>
            <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{card.name}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {card.set_name ?? card.set_code?.toUpperCase()}
            {card.mana_cost ? ` · ${card.mana_cost}` : ''}
            </div>
            </div>
            </div>
    )
}

export default function DeckAddCardModal({ deckId, onClose }) {
    const qc = useQueryClient()
    const inputRef = useRef(null)

    const [query, setQuery] = useState('')
    const [allowNonOwned, setAllowNonOwned] = useState(false)
    const [results, setResults] = useState([])
    const [searching, setSearching] = useState(false)
    const [searched, setSearched] = useState(false)

    const [selectedCard, setSelectedCard] = useState(null)
    const [printings, setPrintings] = useState([])
    const [selectedPrintingId, setSelectedPrintingId] = useState('')
    const [loadingPrintings, setLoadingPrintings] = useState(false)

    const [zone, setZone] = useState('Mainboard')
    const [quantity, setQuantity] = useState(1)
    const [adding, setAdding] = useState(false)

    const activePrinting = allowNonOwned
    ? (printings.find(p => p.scryfall_id === selectedPrintingId) ?? selectedCard)
    : selectedCard

    const search = useCallback(async () => {
        if (query.length < 2) return
            setSearching(true)
            setSearched(true)
            setResults([])
            try {
                const endpoint = allowNonOwned
                ? `/cards/scryfall/search?q=${encodeURIComponent(query)}`
                : `/cards/collection/search?q=${encodeURIComponent(query)}`
                const res = await api.get(endpoint)
                setResults(res.data)
            } finally {
                setSearching(false)
            }
    }, [query, allowNonOwned])

    const selectCard = useCallback(async (card) => {
        setSelectedCard(card)
        if (!allowNonOwned) return

            setSelectedPrintingId(card.scryfall_id)
            setPrintings([card])
            setLoadingPrintings(true)
            try {
                const res = await api.get(`/cards/printings?name=${encodeURIComponent(card.name)}&owned_only=false`)
                const data = res.data.length ? res.data : [card]
                setPrintings(data)
                const match = data.find(p => p.scryfall_id === card.scryfall_id)
                setSelectedPrintingId(match ? match.scryfall_id : data[0].scryfall_id)
            } catch {
                setPrintings([card])
            } finally {
                setLoadingPrintings(false)
            }
    }, [allowNonOwned])

    const addCard = async () => {
        if (!activePrinting) return
            setAdding(true)
            try {
                await api.post(`/decks/${deckId}/cards`, {
                    scryfall_id: activePrinting.scryfall_id,
                    quantity,
                    is_commander: zone === 'Commander',
                    is_sideboard: zone === 'Sideboard',
                })
                qc.invalidateQueries(['deck', deckId])
                onClose()
            } finally {
                setAdding(false)
            }
    }

    const resetToSearch = () => {
        setSelectedCard(null)
        setPrintings([])
        setSelectedPrintingId('')
        setZone('Mainboard')
        setQuantity(1)
        setTimeout(() => inputRef.current?.focus(), 0)
    }

    const handleNonOwnedToggle = (e) => {
        setAllowNonOwned(e.target.checked)
        setResults([])
        setSearched(false)
    }

    return (
        <div className="modal-overlay" onClick={onClose}>
        <div className="modal" style={{ maxWidth: 500 }} onClick={e => e.stopPropagation()}>
        <h2>Add Card to Deck</h2>

        {!selectedCard ? (
            <>
            <div className="search-bar">
            <input
            ref={inputRef}
            autoFocus
            placeholder="Search cards…"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()}
            />
            <button className="btn btn-primary" onClick={search}
            disabled={searching || query.length < 2}>
            <Search size={16} />
            </button>
            </div>

            <label className="flex-gap" style={{ marginBottom: '1rem', cursor: 'pointer', userSelect: 'none' }}>
            <input type="checkbox" checked={allowNonOwned} onChange={handleNonOwnedToggle}
            style={{ width: 'auto' }} />
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Allow non-owned cards
            </span>
            </label>

            {searching && <div className="empty-state"><p>Searching…</p></div>}

            {!searching && results.length > 0 && (
                <div className="search-results">
                {results.map(card => (
                    <CardResult key={card.scryfall_id} card={card} onClick={() => selectCard(card)} />
                ))}
                </div>
            )}

            {!searching && searched && results.length === 0 && (
                <div className="empty-state">
                <p>No {allowNonOwned ? '' : 'owned '}cards found.</p>
                </div>
            )}

            <div className="modal-footer">
            <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
            </div>
            </>
        ) : (
            <>
            <div className="card-preview-block" style={{ alignItems: 'flex-start' }}>
            <div style={{ width: 110, flexShrink: 0, borderRadius: 8,
                overflow: 'hidden', aspectRatio: '63 / 88' }}>
                {activePrinting?.scryfall_id &&
                    <img src={scryfallImg(activePrinting.scryfall_id, 'normal')}
                    alt={activePrinting.name} style={{ width: '100%', display: 'block' }}
                    onError={e => { e.currentTarget.style.display = 'none' }} />}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600 }}>{activePrinting?.name}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {activePrinting?.set_name ?? activePrinting?.set_code?.toUpperCase()}
                    {activePrinting?.mana_cost ? ` · ${activePrinting.mana_cost}` : ''}
                    </div>

                    {allowNonOwned && (
                        <div className="form-group">
                        <label>Set</label>
                        {loadingPrintings
                            ? <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Loading printings…</span>
                            : <select value={selectedPrintingId}
                            onChange={e => setSelectedPrintingId(e.target.value)}>
                            {printings.map(p => (
                                <option key={p.scryfall_id} value={p.scryfall_id}>
                                {p.set_name ?? p.set_code?.toUpperCase()}
                                {p.set_code ? ` (${p.set_code.toUpperCase()})` : ''}
                                </option>
                            ))}
                            </select>
                        }
                        </div>
                    )}

                    <div className="form-grid-2col">
                    <div className="form-group">
                    <label>Zone</label>
                    <select value={zone} onChange={e => setZone(e.target.value)}>
                    {ZONES.map(z => <option key={z} value={z}>{z}</option>)}
                    </select>
                    </div>
                    <div className="form-group">
                    <label>Quantity</label>
                    <input type="number" min={1} value={quantity}
                    onChange={e => setQuantity(Math.max(1, parseInt(e.target.value) || 1))} />
                    </div>
                    </div>
                    </div>
                    </div>

                    <div className="modal-footer">
                    <button className="btn btn-ghost" onClick={resetToSearch}>Back</button>
                    <button className="btn btn-primary" onClick={addCard}
                    disabled={adding || !activePrinting}>
                    {adding ? 'Adding…' : 'Add to Deck'}
                    </button>
                    </div>
                    </>
        )}
        </div>
        </div>
    )
}

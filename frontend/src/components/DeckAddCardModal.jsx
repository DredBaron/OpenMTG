import { useState, useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import api from '../api'
import SetPicker from './SetPicker'

const ZONES = ['Mainboard', 'Sideboard', 'Commander']

function scryfallImg(scryfallId, size = 'small') {
    if (!scryfallId) return null
    return `https://cards.scryfall.io/${size}/front/${scryfallId[0]}/${scryfallId[1]}/${scryfallId}.jpg`
}

function CardResult({ card, onClick }) {
    const [imgError, setImgError] = useState(false)

    return (
        <div className="search-result-item" onClick={onClick}>
            <div className="deck-card-thumb-wrap">
                {!imgError
                    ? <img
                        src={scryfallImg(card.scryfall_id, 'small')}
                        alt=""
                        className="deck-card-thumb-img"
                        onError={() => setImgError(true)}
                    />
                    : <span className="deck-card-thumb-fallback">
                        {card.set_code?.toUpperCase()}
                    </span>
                }
            </div>
            <div>
                <div className="card-result-name">{card.name}</div>
                <div className="text-muted-xs">
                    {card.set_name ?? card.set_code?.toUpperCase()}
                    {card.mana_cost ? ` | ${card.mana_cost}` : ''}
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
    const [zone, setZone] = useState('Mainboard')
    const [quantity, setQuantity] = useState(1)
    const [adding, setAdding] = useState(false)

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

    const selectCard = useCallback((card) => {
        setSelectedCard(card)
    }, [])

    const addCard = async () => {
        if (!selectedCard) return
        setAdding(true)
        try {
            await api.post(`/decks/${deckId}/cards`, {
                scryfall_id: selectedCard.scryfall_id,
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
            <div className="modal modal-max-sm" onClick={e => e.stopPropagation()}>
                <h2>Add Card to Deck</h2>

                {!selectedCard ? (
                    <>
                        <div className="search-bar">
                            <input
                                ref={inputRef}
                                autoFocus
                                placeholder="Search cards"
                                value={query}
                                onChange={e => setQuery(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && search()}
                            />
                            <button
                                className="btn btn-primary"
                                onClick={search}
                                disabled={searching || query.length < 2}
                            >
                                <Search size={16} />
                            </button>
                        </div>

                        <label className="flex-gap allow-non-owned">
                            <input
                                type="checkbox"
                                checked={allowNonOwned}
                                onChange={handleNonOwnedToggle}
                                style={{ width: 'auto' }}
                            />
                            <span className="text-muted-sm">
                                Allow non-owned cards
                            </span>
                        </label>

                        {searching && <div className="empty-state"><p>Searching</p></div>}

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
                        <div className="card-preview-block">
                            {selectedCard?.scryfall_id &&
                                <img
                                    src={scryfallImg(selectedCard.scryfall_id, 'small')}
                                    alt={selectedCard.name}
                                    className="card-thumb-md"
                                    onError={e => { e.currentTarget.style.display = 'none' }}
                                />
                            }
                            <div>
                                <div className="card-preview-name">{selectedCard?.name}</div>
                                <div className="card-preview-meta">
                                    {selectedCard?.set_name ?? selectedCard?.set_code?.toUpperCase()}
                                    {selectedCard?.mana_cost ? ` | ${selectedCard.mana_cost}` : ''}
                                </div>
                                <button onClick={resetToSearch} className="btn-link">
                                    Change card
                                </button>
                            </div>
                        </div>

                        {allowNonOwned && (
                            <div style={{ marginBottom: '1rem' }}>
                                <SetPicker card={selectedCard} onSelect={setSelectedCard} />
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
                                <input
                                    type="number"
                                    min={1}
                                    value={quantity}
                                    onChange={e => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                                />
                            </div>
                        </div>

                        <div className="modal-footer">
                            <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
                            <button
                                className="btn btn-primary"
                                onClick={addCard}
                                disabled={adding || !selectedCard}
                            >
                                {adding ? 'Adding' : 'Add to Deck'}
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    )
}

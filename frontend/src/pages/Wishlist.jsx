import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Trash2, Bell, TrendingDown, Plus, X, Check, Eye, Pencil, BarChart2, LayoutGrid, List, } from 'lucide-react'
import api from '../api'
import { useCurrency } from '../hooks/useCurrency'
import { useIsMobile } from '../hooks/useIsMobile'
import { usePersistedView } from '../hooks/usePersistedView'
import { formatPrice, resolvePrice } from '../utils/currency'
import SetPicker from '../components/SetPicker'

function PriceLineChart({ data, currency, market, foil }) {
    const prices = data.map(d => resolvePrice(d, currency, foil, market))

    const validPts = data
        .map((d, i) => ({ d, i, price: prices[i] }))
        .filter(p => p.price != null)

    if (validPts.length === 0) return (
        <div className="empty-state" style={{ padding: '1.5rem' }}>
            <p>No price data recorded for this currency yet.</p>
        </div>
    )

    const W = 400, H = 140
    const pL = 50, pB = 24, pT = 8, pR = 10
    const plotW = W - pL - pR
    const plotH = H - pT - pB

    const vals = validPts.map(p => p.price)
    const minP = Math.min(...vals)
    const maxP = Math.max(...vals)
    const range = maxP - minP || 0.01

    const xOf = i => pL + (i / Math.max(validPts.length - 1, 1)) * plotW
    const yOf = p => pT + plotH - ((p - minP) / range) * plotH

    const pts = validPts.map((p, i) => ({
        x: xOf(i),
        y: yOf(p.price),
        price: p.price,
        date: p.d.recorded_at,
    }))

    const pathD = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')

    const yLabels = [minP, (minP + maxP) / 2, maxP]
    const xIndices = validPts.length > 2
        ? [0, Math.floor((validPts.length - 1) / 2), validPts.length - 1]
        : validPts.length === 2 ? [0, 1] : [0]

    return (
        <svg viewBox={`0 0 ${W} ${H}`} className="price-chart-svg">
            {yLabels.map((p, i) => {
                const y = yOf(p)
                return (
                    <g key={i}>
                        <line x1={pL} y1={y} x2={W - pR} y2={y}
                            stroke="var(--border)" strokeWidth={1} strokeDasharray="3,3" />
                        <text x={pL - 4} y={y + 4} textAnchor="end"
                            fontSize={9} fill="var(--text-muted)" fontFamily="monospace">
                            {formatPrice(p, currency, market)}
                        </text>
                    </g>
                )
            })}

            {xIndices.map(i => (
                <text key={i} x={pts[i].x} y={H - 2}
                    textAnchor="middle" fontSize={8} fill="var(--text-muted)">
                    {new Date(pts[i].date).toLocaleDateString()}
                </text>
            ))}

            <path d={pathD} fill="none" stroke="var(--accent)" strokeWidth={2} strokeLinejoin="round" />

            {pts.map((p, i) => (
                <circle key={i} cx={p.x} cy={p.y} r={3}
                    fill="var(--accent)" stroke="var(--surface)" strokeWidth={1.5} />
            ))}
        </svg>
    )
}

function PriceHistoryModal({ entry, currency, market, onClose }) {
    const [showFoil, setShowFoil] = useState(entry.foil)
    const hasFoilPrices = entry.price_usd_foil != null || entry.price_eur_foil != null

    const { data: history = [], isLoading } = useQuery({
        queryKey: ['wishlist-history', entry.id],
        queryFn: () => api.get(`/wishlist/${entry.id}/history?days=90`).then(r => r.data),
    })

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={e => e.stopPropagation()}>
                <h2>Price History</h2>
                <div className="card-preview-name">{entry.name}</div>
                <div className="card-preview-meta">{entry.set_name} #{entry.rarity}</div>

                {hasFoilPrices && (
                    <label className="foil-label mt-sm" style={{ paddingTop: 0 }}>
                        <input type="checkbox" className="input-check"
                            checked={showFoil} onChange={e => setShowFoil(e.target.checked)} />
                        Show foil prices
                    </label>
                )}

                <div style={{ marginTop: '1rem' }}>
                    {isLoading && <div className="loading">Loading...</div>}

                    {!isLoading && history.length === 0 && (
                        <div className="empty-state" style={{ padding: '1.5rem' }}>
                            <Bell size={24} />
                            <p>No history recorded yet.</p>
                            <p>Prices are captured each time the refresh scheduler runs. History accumulates going forward from time of card addition to the watchlist as Scryfall does not provide historical price data.</p>
                        </div>
                    )}

                    {!isLoading && history.length > 0 && (
                        <PriceLineChart data={history} currency={currency} market={market} foil={showFoil} />
                    )}
                </div>

                <div className="modal-footer">
                    <button className="btn btn-ghost" onClick={onClose}>Close</button>
                </div>
            </div>
        </div>
    )
}

function WishlistEditModal({ entry, currency, onUpdate, onClose }) {
    const [targetVal, setTargetVal] = useState(entry.target_price ?? '')
    const [foil, setFoil] = useState(entry.foil)
    const [selected, setSelected] = useState({
        scryfall_id:      entry.scryfall_id,
        image_uri:        entry.image_uri,
        set_name:         entry.set_name,
        set_code:         entry.set_code,
        rarity:           entry.rarity,
        collector_number: entry.collector_number,
        price_usd:        entry.price_usd,
        price_usd_foil:   entry.price_usd_foil,
        price_eur:        entry.price_eur,
        price_eur_foil:   entry.price_eur_foil,
    })

    const save = () => {
        const parsed = targetVal !== '' ? parseFloat(targetVal) : null
        onUpdate(entry.id, { scryfall_id: selected.scryfall_id, foil, target_price: parsed })
        onClose()
    }

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
                <h2>Edit Wishlist Entry</h2>
                <div className="card-preview-block">
                    {selected.image_uri &&
                        <img src={selected.image_uri} alt={entry.name} className="wishlist-selected-img" />}
                    <div className="flex-fill">
                        <div className="card-preview-name">{entry.name}</div>
                        <div className="card-preview-meta">{selected.set_name} #{selected.rarity}</div>
                    </div>
                </div>
                <div style={{ marginBottom: '0.75rem' }}>
                    <SetPicker
                        card={selected}
                        onSelect={(printing) => setSelected(prev => ({
                            ...prev,
                            scryfall_id:      printing.scryfall_id,
                            set_code:         printing.set_code,
                            set_name:         printing.set_name,
                            collector_number: printing.collector_number,
                            rarity:           printing.rarity,
                            image_uri:        printing.image_uri,
                            image_uri_small:  printing.image_uri_small,
                            price_usd:        printing.price_usd,
                            price_usd_foil:   printing.price_usd_foil,
                            price_eur:        printing.price_eur,
                            price_eur_foil:   printing.price_eur_foil,
                        }))}
                    />
                </div>
                <label className="foil-label foil-label-edit">
                    <input type="checkbox" className="input-check"
                        checked={foil} onChange={e => setFoil(e.target.checked)} />
                    Foil
                </label>
                <div className="form-group">
                    <label>Target price ({currency.toUpperCase()})</label>
                    <input
                        type="number" min={0} step={0.01}
                        value={targetVal}
                        placeholder="Leave empty to watch without a target"
                        onChange={e => setTargetVal(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && save()}
                    />
                </div>
                <div className="modal-footer">
                    <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
                    <button className="btn btn-primary" onClick={save}>Save</button>
                </div>
            </div>
        </div>
    )
}

function WishlistCardViewer({ entry, onClose }) {
    const largeImage = entry.image_uri?.replace('/normal/', '/large/') || entry.image_uri
    const scryfallUrl = `https://scryfall.com/search?q=${encodeURIComponent(entry.name)}`

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="wishlist-viewer" onClick={e => e.stopPropagation()}>
                {largeImage &&
                    <img src={largeImage} alt={entry.name} className="wishlist-viewer-img" />}
                <a href={scryfallUrl} target="_blank" rel="noreferrer"
                    className="btn btn-primary" style={{ textDecoration: 'none' }}>
                    View on Scryfall
                </a>
            </div>
        </div>
    )
}

function PriceBadge({ current, target, currency, market }) {
    if (current == null) return null

    const met = target != null && current <= target
    const diff = target != null ? ((current - target) / target) * 100 : null

    return (
        <div className="price-badge">
            <span className={`price-current ${met ? 'price-met' : 'price-watching'}`}>
                {formatPrice(current, currency, market)}
            </span>
            {target != null && (
                <span className={`price-badge-label ${met ? 'price-met' : ''}`}>
                    {met
                        ? <><Check size={11} /> target {formatPrice(target, currency, market)}</>
                        : <>{diff != null ? `+${diff.toFixed(0)}%` : ''} of target</>
                    }
                </span>
            )}
        </div>
    )
}

function AddCardPanel({ currency, market, onAdded }) {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState([])
    const [searching, setSearching] = useState(false)
    const [selected, setSelected] = useState(null)
    const [targetPrice, setTargetPrice] = useState('')
    const [foil, setFoil] = useState(false)
    const [error, setError] = useState('')
    const qc = useQueryClient()

    const search = async () => {
        if (query.length < 2) return
        setSearching(true)
        setError('')
        setResults([])
        setSelected(null)
        try {
            try {
                const res = await api.get(`/cards/named?name=${encodeURIComponent(query)}`)
                setSelected(res.data)
            } catch {
                const res = await api.get(`/cards/search?q=${encodeURIComponent(query)}`)
                setResults(res.data)
            }
        } catch {
            setError('No cards found.')
        } finally {
            setSearching(false)
        }
    }

    const add = async () => {
        if (!selected) return
        try {
            await api.post('/wishlist', {
                scryfall_id: selected.scryfall_id,
                target_price: targetPrice !== '' ? parseFloat(targetPrice) : null,
                foil,
            })
            qc.invalidateQueries(['wishlist'])
            onAdded?.()
            setQuery('')
            setResults([])
            setSelected(null)
            setTargetPrice('')
            setFoil(false)
        } catch (e) {
            setError(e?.response?.data?.detail || 'Could not add card.')
        }
    }

    return (
        <div className="wishlist-add-panel">

            <div className="search-bar">
                <input
                    autoFocus
                    placeholder="Search for a card to watch..."
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && search()}
                />
                <button className="btn btn-primary" onClick={search} disabled={searching || query.length < 2}>
                    {searching ? '...' : <Search size={16} />}
                </button>
            </div>

            {error && <div className="error">{error}</div>}

            {results.length > 0 && !selected && (
                <div className="wishlist-result-list">
                    {results.map(card => (
                        <div
                            key={card.scryfall_id}
                            className="search-result-item"
                            onClick={() => { setSelected(card); setResults([]) }}
                        >
                            {card.image_uri_small &&
                                <img src={card.image_uri_small} alt={card.name} className="wishlist-result-img" />}
                            <div className="flex-fill">
                                <div className="wishlist-result-name">{card.name}</div>
                                <div className="card-preview-meta">{card.set_name} #{card.rarity}</div>
                            </div>
                            {resolvePrice(card, currency, false, market) != null &&
                                <span className="text-gold text-sm" style={{ fontWeight: 600 }}>
                                    {formatPrice(resolvePrice(card, currency, false, market), currency, market)}
                                </span>}
                        </div>
                    ))}
                </div>
            )}

            {selected && (
                <div className="wishlist-selected-card">
                    {selected.image_uri_small &&
                        <img src={selected.image_uri_small} alt={selected.name} className="wishlist-selected-img" />}

                    <div className="flex-fill">
                        <div className="wishlist-selected-name">{selected.name}</div>
                        <div className="wishlist-card-meta">
                            {selected.set_name} #{selected.rarity}
                            {resolvePrice(selected, currency, false, market) != null &&
                                <span className="text-gold" style={{ marginLeft: '0.5rem' }}>
                                    {formatPrice(resolvePrice(selected, currency, false, market), currency, market)}
                                </span>}
                        </div>

                        <div className="wishlist-add-fields">
                            <div className="form-group form-group-flex">
                                <label>Target price ({currency.toUpperCase()})</label>
                                <input
                                    type="number" min={0} step={0.01}
                                    placeholder="e.g. 4.99"
                                    value={targetPrice}
                                    onChange={e => setTargetPrice(e.target.value)}
                                />
                            </div>
                            <label className="foil-label">
                                <input type="checkbox" checked={foil}
                                    onChange={e => setFoil(e.target.checked)} className="input-check" />
                                Foil
                            </label>
                        </div>
                    </div>

                    <button className="btn btn-ghost btn-icon" onClick={() => setSelected(null)}>
                        <X size={14} />
                    </button>
                </div>
            )}

            {selected && (
                <div style={{ marginBottom: '0.75rem' }}>
                    <SetPicker
                        card={selected}
                        onSelect={(printing) => setSelected(prev => ({
                            ...prev,
                            scryfall_id: printing.scryfall_id,
                            set_code: printing.set_code,
                            set_name: printing.set_name,
                            collector_number: printing.collector_number,
                            rarity: printing.rarity,
                            image_uri: printing.image_uri,
                            image_uri_small: printing.image_uri_small,
                            price_usd: printing.price_usd,
                            price_usd_foil: printing.price_usd_foil,
                            price_eur: printing.price_eur,
                            price_eur_foil: printing.price_eur_foil,
                        }))}
                    />
                </div>
            )}

            {selected && (
                <div className="wishlist-add-actions">
                    <button className="btn btn-ghost" onClick={() => { setSelected(null); setResults([]) }}>
                        Cancel
                    </button>
                    <button className="btn btn-primary" onClick={add}>
                        <Plus size={15} /> Add to Wishlist
                    </button>
                </div>
            )}

        </div>
    )
}

// Grid

function WishlistGridCard({ entry, currency, market, onDelete, onEdit, onHistory, onView }) {
    const [hovered, setHovered] = useState(false)
    const [confirmDelete, setConfirmDelete] = useState(false)

    const currentPrice = resolvePrice(entry, currency, entry.foil, market)
    const priceMet = entry.target_price != null && currentPrice != null && currentPrice <= entry.target_price

    return (
        <div
            className="wishlist-grid-card"
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => { setHovered(false); setConfirmDelete(false) }}
        >
            <div className="deck-grid-item">
                {entry.image_uri && <img src={entry.image_uri} alt={entry.name} />}

                {priceMet && (
                    <div className="deck-grid-qty" style={{ background: 'var(--success)' }}>
                        <Check size={10} />
                    </div>
                )}

                {hovered && (
                    <div className="deck-grid-overlay">
                        <button className="btn btn-ghost btn-sm btn-block"
                            onClick={e => { e.stopPropagation(); onView(entry) }}>
                            <Eye size={13} /> View
                        </button>
                        <button className="btn btn-ghost btn-sm btn-block"
                            onClick={e => { e.stopPropagation(); onEdit(entry) }}>
                            <Pencil size={13} /> Edit
                        </button>
                        <button className="btn btn-ghost btn-sm btn-block"
                            onClick={e => { e.stopPropagation(); onHistory(entry) }}>
                            <BarChart2 size={13} /> History
                        </button>
                        {confirmDelete ? (
                            <button className="btn btn-danger btn-sm btn-block"
                                onClick={e => { e.stopPropagation(); onDelete(entry.id) }}>
                                <Trash2 size={13} /> Sure?
                            </button>
                        ) : (
                            <button className="btn btn-ghost btn-sm btn-block"
                                onClick={e => { e.stopPropagation(); setConfirmDelete(true) }}>
                                <Trash2 size={13} /> Delete
                            </button>
                        )}
                    </div>
                )}
            </div>

            {currentPrice != null && (
                <div className="wishlist-grid-price" style={{
                    color: priceMet ? 'var(--success)' : 'var(--gold)',
                }}>
                    {formatPrice(currentPrice, currency, market)}
                </div>
            )}
            {entry.target_price != null && (
                <div className="wishlist-grid-target">
                    <TrendingDown size={10} /> {formatPrice(entry.target_price, currency, market)}
                </div>
            )}
        </div>
    )
}

// List

function WishlistRow({ entry, currency, market, onDelete, onEdit, onHistory, isMobile }) {
    const currentPrice = resolvePrice(entry, currency, entry.foil, market)

    if (isMobile) {
        return (
            <div className="wishlist-mobile-row">
                {entry.image_uri
                    ? <img src={entry.image_uri} alt={entry.name} className="wishlist-row-img" />
                    : <div className="wishlist-row-img-placeholder">{entry.set_code?.toUpperCase()}</div>}
                <div className="wishlist-mobile-body">
                    <div className="wishlist-mobile-top">
                        <div className="wishlist-mobile-name-wrap">
                            <div className="wishlist-row-name">
                                {entry.name}
                                {entry.foil &&
                                    <span className="badge badge-foil" style={{ marginLeft: '0.4rem' }}>FOIL</span>}
                            </div>
                            <div className="card-preview-meta">
                                {entry.set_code?.toUpperCase()} #{entry.collector_number}
                            </div>
                        </div>
                        <PriceBadge current={currentPrice} target={entry.target_price} currency={currency} market={market} />
                    </div>
                    <div className="wishlist-mobile-actions">
                        <button className="btn btn-ghost btn-icon" onClick={() => onEdit(entry)} title="Edit target price">
                            <Pencil size={15} />
                        </button>
                        <button className="btn btn-ghost btn-icon" onClick={() => onHistory(entry)} title="Price history">
                            <BarChart2 size={15} />
                        </button>
                        <button className="btn btn-ghost btn-icon" onClick={() => onDelete(entry.id)} title="Remove from wishlist">
                            <Trash2 size={15} />
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="wishlist-row">
            {entry.image_uri
                ? <img src={entry.image_uri} alt={entry.name} className="wishlist-row-img" />
                : <div className="wishlist-row-img-placeholder">{entry.set_code?.toUpperCase()}</div>}
            <div className="flex-fill">
                <div className="wishlist-row-name">
                    {entry.name}
                    {entry.foil &&
                        <span className="badge badge-foil" style={{ marginLeft: '0.4rem' }}>FOIL</span>}
                </div>
                <div className="card-preview-meta">
                    {entry.set_name} #{entry.collector_number} | {entry.rarity}
                </div>
            </div>
            <div className="wishlist-target-col">
                {entry.target_price != null
                    ? <span className="wishlist-target-text">
                        <TrendingDown size={12} /> {formatPrice(entry.target_price, currency, market)}
                      </span>
                    : <span className="wishlist-target-text wishlist-target-none">-</span>}
            </div>
            <div className="wishlist-price-col">
                <PriceBadge current={currentPrice} target={entry.target_price} currency={currency} market={market} />
            </div>
            <button className="btn btn-ghost btn-icon" onClick={() => onEdit(entry)} title="Edit target price">
                <Pencil size={15} />
            </button>
            <button className="btn btn-ghost btn-icon" onClick={() => onHistory(entry)} title="Price history">
                <BarChart2 size={15} />
            </button>
            <button className="btn btn-ghost btn-icon" onClick={() => onDelete(entry.id)} title="Remove from wishlist">
                <Trash2 size={15} />
            </button>
        </div>
    )
}

export default function Wishlist() {
    useEffect(() => { document.title = 'Wishlist - OpenMTG' }, [])

    const qc = useQueryClient()
    const { currency, market } = useCurrency()
    const isMobile = useIsMobile()
    const [adding, setAdding] = useState(false)
    const [filter, setFilter] = useState('all')
    const [viewMode, setViewMode] = usePersistedView('wishlist-view', 'list')
    const [historyEntry, setHistoryEntry] = useState(null)
    const [editingEntry, setEditingEntry] = useState(null)
    const [viewingEntry, setViewingEntry] = useState(null)

    const { data: entries = [], isLoading, isError } = useQuery({
        queryKey: ['wishlist'],
        queryFn: () => api.get('/wishlist').then(r => r.data),
    })

    const deleteMutation = useMutation({
        mutationFn: (id) => api.delete(`/wishlist/${id}`),
        onSuccess: () => qc.invalidateQueries(['wishlist']),
    })

    const updateMutation = useMutation({
        mutationFn: ({ id, scryfall_id, foil, target_price }) =>
            api.patch(`/wishlist/${id}`, { scryfall_id, foil, target_price }),
        onSuccess: () => qc.invalidateQueries(['wishlist']),
    })

    const priceMet = (e) => {
        const cur = resolvePrice(e, currency, e.foil, market)
        return e.target_price != null && cur != null && cur <= e.target_price
    }

    const filtered = entries.filter(e => {
        if (filter === 'met') return priceMet(e)
        if (filter === 'watching') return e.target_price != null && !priceMet(e)
        return true
    })
    const metCount = entries.filter(e => priceMet(e)).length

    const gridProps = {
        currency,
        market,
        onDelete: (id) => deleteMutation.mutate(id),
        onEdit: setEditingEntry,
        onHistory: setHistoryEntry,
        onView: setViewingEntry,
    }

    return (
        <div className="wishlist-page">

            <div className="page-header">
                <div>
                    <h1>Wishlist</h1>
                    {entries.length > 0 && (
                        <p className="page-subtitle">
                            {entries.length} card{entries.length !== 1 ? 's' : ''} watched
                            {metCount > 0 &&
                                <span className="save-success" style={{ marginLeft: '0.5rem' }}>
                                    {metCount} at target price
                                </span>}
                        </p>
                    )}
                </div>
                <div className="flex-gap">
                    <div className="btn-group">
                        <button
                            className={`btn btn-sm ${viewMode === 'list' ? 'btn-primary' : 'btn-ghost'}`}
                            onClick={() => setViewMode('list')} title="List view">
                            <List size={15} />
                        </button>
                        <button
                            className={`btn btn-sm ${viewMode === 'grid' ? 'btn-primary' : 'btn-ghost'}`}
                            onClick={() => setViewMode('grid')} title="Grid view">
                            <LayoutGrid size={15} />
                        </button>
                    </div>
                    <button className="btn btn-primary btn-sm" onClick={() => setAdding(v => !v)}>
                        {adding ? <><X size={15} /> Cancel</> : <><Plus size={15} /> Add Card</>}
                    </button>
                </div>
            </div>

            {adding && <AddCardPanel currency={currency} market={market} onAdded={() => setAdding(false)} />}

            {entries.length > 0 && (
                <div className="wishlist-filters">
                    {[
                        { key: 'all', label: 'All' },
                        { key: 'met', label: `At target (${metCount})` },
                        { key: 'watching', label: 'Watching' },
                    ].map(tab => (
                        <button
                            key={tab.key}
                            className={`wishlist-filter-btn ${filter === tab.key ? 'active' : ''}`}
                            onClick={() => setFilter(tab.key)}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            )}

            {isLoading && <div className="loading">Loading wishlist...</div>}
            {isError && <div className="error">Failed to load wishlist.</div>}

            {!isLoading && !isError && entries.length === 0 && !adding && (
                <div className="empty-state">
                    <Bell size={32} />
                    <p>Your wishlist is empty.</p>
                    <p>Pin cards to track their prices and get notified when they hit your target.</p>
                    <button className="btn btn-primary mt-sm" onClick={() => setAdding(true)}>
                        <Plus size={15} /> Add your first card
                    </button>
                </div>
            )}

            {!isLoading && filtered.length > 0 && viewMode === 'grid' && (
                <div className="deck-grid">
                    {filtered.map(entry => (
                        <WishlistGridCard key={entry.id} entry={entry} {...gridProps} />
                    ))}
                </div>
            )}

            {!isLoading && filtered.length > 0 && viewMode === 'list' && (
                <div className="wishlist-list">
                    {!isMobile && (
                        <div className="wishlist-table-header">
                            <div />
                            <div className="wishlist-col-label">Card</div>
                            <div className="wishlist-col-label">Target</div>
                            <div className="wishlist-col-label" style={{ textAlign: 'right' }}>Current</div>
                            <div />
                            <div />
                            <div />
                        </div>
                    )}
                    {filtered.map(entry => (
                        <WishlistRow
                            key={entry.id}
                            entry={entry}
                            currency={currency}
                            market={market}
                            isMobile={isMobile}
                            onDelete={(id) => deleteMutation.mutate(id)}
                            onEdit={setEditingEntry}
                            onHistory={setHistoryEntry}
                        />
                    ))}
                </div>
            )}

            {!isLoading && entries.length > 0 && filtered.length === 0 && (
                <div className="empty-state">
                    <p>No cards match this filter.</p>
                </div>
            )}

            {historyEntry && (
                <PriceHistoryModal entry={historyEntry} currency={currency} market={market} onClose={() => setHistoryEntry(null)} />
            )}
            {editingEntry && (
                <WishlistEditModal
                    entry={editingEntry}
                    currency={currency}
                    onUpdate={(id, data) => updateMutation.mutate({ id, ...data })}
                    onClose={() => setEditingEntry(null)}
                />
            )}
            {viewingEntry && (
                <WishlistCardViewer entry={viewingEntry} onClose={() => setViewingEntry(null)} />
            )}

        </div>
    )
}

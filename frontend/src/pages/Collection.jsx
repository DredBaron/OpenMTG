import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Pencil, Trash2, Download, Upload, ChevronLeft, ChevronRight, SlidersHorizontal, Star, MoreVertical } from 'lucide-react'
import api from '../api'
import SetPicker from '../components/SetPicker'
import ImportModal from '../components/ImportModal'
import { downloadFile } from '../utils/downloadFile';

const CONDITION_MULTIPLIERS = {
  NM:  1.0,
  LP:  0.75,
  MP:  0.50,
  HP:  0.25,
  DMG: 0.10,
}

function getPrice(entry) {
  const base = entry.foil
  ? (entry.card.price_usd_foil || entry.card.price_usd)
  : entry.card.price_usd
  if (!base) return null
    const multiplier = CONDITION_MULTIPLIERS[entry.condition] ?? 1.0
    return (base * multiplier).toFixed(2)
}

function getPriceColor(entry) {
  return entry.foil ? '#c09af0' : 'var(--gold)'
}

function AddCardModal({ onClose }) {
  const qc = useQueryClient()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState(null)
  const [form, setForm] = useState({ quantity: 1, condition: 'NM', foil: false, language: 'en' })
  const [searching, setSearching] = useState(false)

  const search = async () => {
    if (query.length < 2) return
    setSearching(true)
    try {
      const res = await api.get(`/cards/search?q=${encodeURIComponent(query)}`)
      setResults(res.data)
    } finally {
      setSearching(false)
    }
  }

  const add = useMutation({
    mutationFn: () => api.post('/collection', { scryfall_id: selected.scryfall_id, ...form }),
    onSuccess: () => { qc.invalidateQueries(['collection']); onClose() }
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Add Card</h2>
        <div className="search-bar">
          <input placeholder="Search Scryfall…" value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()} />
          <button className="btn btn-primary" onClick={search} disabled={searching}>
            <Search size={16} />
          </button>
        </div>

        {results.length > 0 && !selected && (
          <div style={{ maxHeight: 240, overflowY: 'auto', marginBottom: '1rem' }}>
            {results.map(card => (
              <div key={card.scryfall_id}
                onClick={() => setSelected(card)}
                style={{ display: 'flex', gap: '0.75rem', alignItems: 'center',
                  padding: '0.5rem', borderRadius: 'var(--radius)', cursor: 'pointer',
                  borderBottom: '1px solid var(--border)' }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--surface2)'}
                onMouseLeave={e => e.currentTarget.style.background = ''}>
                {card.image_uri &&
                  <img src={card.image_uri} alt={card.name}
                    style={{ width: 36, borderRadius: 4 }} />}
                <div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{card.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {card.set_name} · {card.rarity}
                    {card.price_usd && ` · $${card.price_usd}`}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {selected && (
          <>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center',
              padding: '0.75rem', background: 'var(--surface2)',
              borderRadius: 'var(--radius)', marginBottom: '1rem' }}>
              {selected.image_uri &&
                <img src={selected.image_uri} alt={selected.name}
                  style={{ width: 48, borderRadius: 4 }} />}
              <div>
                <div style={{ fontWeight: 600 }}>{selected.name}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{selected.set_name}</div>
                <button onClick={() => setSelected(null)}
                  style={{ fontSize: '0.75rem', color: 'var(--accent)',
                    background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
                  Change card
                </button>
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <SetPicker
                card={selected}
                onSelect={(printing) => {
                  setSelected(prev => ({
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
                }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
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
          </>
        )}

        <div className="modal-footer">
          <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
          {selected &&
            <button className="btn btn-primary" onClick={() => add.mutate()}
              disabled={add.isPending}>
              {add.isPending ? 'Adding…' : 'Add to Collection'}
            </button>}
        </div>
      </div>
    </div>
  )
}

function EditModal({ entry, onClose }) {
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

  const save = useMutation({
    mutationFn: () => api.patch(`/collection/${entry.id}`, form),
    onSuccess: () => { qc.invalidateQueries(['collection']); onClose() }
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <h2>Edit: {entry.card.name}</h2>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center',
          padding: '0.75rem', background: 'var(--surface2)',
          borderRadius: 'var(--radius)', marginBottom: '1rem' }}>
          {card.image_uri &&
            <img src={card.image_uri} alt={card.name}
              style={{ width: 48, borderRadius: 4, flexShrink: 0 }} />}
          <div>
            <div style={{ fontWeight: 600 }}>{card.name}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {card.set_name} · #{card.collector_number}
            </div>
            {card.price_usd &&
              <div style={{ fontSize: '0.8rem', color: 'var(--gold)' }}>
                ${card.price_usd}
                {card.price_usd_foil &&
                  <span style={{ color: '#c09af0', marginLeft: '0.4rem' }}>
                    ${card.price_usd_foil} foil
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

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
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

function CardImageModal({ card, onClose }) {
  const largeImage = card.image_uri ? card.image_uri.replace('/normal/', '/large/') : null
  const gathererUrl = `https://gatherer.wizards.com/Pages/Card/Details.aspx?name=${encodeURIComponent(card.name)}`

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div onClick={e => e.stopPropagation()}
        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
        {largeImage && (
          <img src={largeImage} alt={card.name}
            style={{ borderRadius: 16, maxWidth: '90vw', maxHeight: '80vh', boxShadow: '0 8px 32px rgba(0,0,0,0.6)' }} />
        )}
        <a href={gathererUrl} target="_blank" rel="noreferrer"
          className="btn btn-primary"
          style={{ textDecoration: 'none' }}>
          View Rulings on Gatherer
        </a>
      </div>
    </div>
  )
}

export default function Collection() {

  useEffect(() => { document.title = 'Collection - OpenMTG' }, [])

  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [editing, setEditing] = useState(null);
  const [viewingCard, setViewingCard] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [showColMenu, setShowColMenu] = useState(false);
  const [colMenuAlign, setColMenuAlign] = useState('right');
  const colMenuBtnRef = useRef(null);
  const [openMenuId, setOpenMenuId] = useState(null);

  const openColMenu = () => {
    if (colMenuBtnRef.current) {
      const rect = colMenuBtnRef.current.getBoundingClientRect();
      setColMenuAlign(rect.left < window.innerWidth / 2 ? 'left' : 'right');
    }
    setShowColMenu(v => !v);
  };
  const onMobile = /Mobile/i.test(navigator.userAgent);
  const [visibleCols, setVisibleCols] = useState({
    image: true, card: true,
    set:       !onMobile,
    qty:       true,
    condition: !onMobile,
    price:     true,
    notes:     !onMobile,
  });
  const toggleCol = (col) => setVisibleCols(prev => ({ ...prev, [col]: !prev[col] }));

  const [sortBy, setSortBy] = useState(null);
  const [sortOrder, setSortOrder] = useState('asc');

  const [filters, setFilters] = useState({
    colors: [],
    foil: null,
    rarity: [],
    favoritesOnly: false,
  });

  const [perPage, setPerPage] = useState(20);
  const [currentPage, setCurrentPage] = useState(1);

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['collection'],
    queryFn: () => api.get('/collection').then(r => r.data),
  });

  const remove = useMutation({
    mutationFn: (id) => api.delete(`/collection/${id}`),
    onSuccess: () => qc.invalidateQueries(['collection']),
  });

  const bulkRemove = useMutation({
    mutationFn: (ids) => Promise.all([...ids].map(id => api.delete(`/collection/${id}`))),
    onSuccess: () => { qc.invalidateQueries(['collection']); setSelectedIds(new Set()) },
  });

  const toggleFavorite = useMutation({
    mutationFn: (entry) => api.patch(`/collection/${entry.id}`, { is_favorite: !entry.is_favorite }),
    onSuccess: () => qc.invalidateQueries(['collection']),
  });

  const toggleSelect = (id) => setSelectedIds(prev => {
    const next = new Set(prev)
    if (next.has(id)) next.delete(id); else next.add(id)
    return next
  });

  const totalValue = entries.reduce((sum, e) => {
    const price = getPrice(e);
    return sum + (price ? parseFloat(price) * e.quantity : 0);
  }, 0);

  const COLOR_CODES = { White: 'W', Red: 'R', Green: 'G', Blue: 'U', Black: 'B' };

  const getCardCastingColors = (card) => {
    if (!card.mana_cost) return [];
    return Object.values(COLOR_CODES).filter(c => card.mana_cost.includes(c));
  };

  const searchScore = (entry, q) => {
    const name = entry.card.name.toLowerCase()
    const set = (entry.card.set_name || '').toLowerCase()
    if (name === q)          return 0
    if (name.startsWith(q))  return 1
    if (name.includes(q))    return 2
    if (set.startsWith(q))   return 3
    if (set.includes(q))     return 4
    return 5
  }

  let displayedEntries = entries
  .filter(entry => {
    const cardColors = getCardCastingColors(entry.card);

    if (filters.colors.length > 0) {
      const selectedColors = filters.colors.map(fc => COLOR_CODES[fc]);
      if (!cardColors.some(c => selectedColors.includes(c))) return false;
    }

    if (filters.foil !== null && entry.foil !== filters.foil) return false;
    if (filters.favoritesOnly && !entry.is_favorite) return false;

    if (filters.rarity.length > 0 && !filters.rarity.map(r => r.toLowerCase()).includes(entry.card.rarity)) return false;

    if (search) {
      const q = search.toLowerCase()
      const nameMatch = entry.card.name.toLowerCase().includes(q)
      const setMatch = (entry.card.set_name || '').toLowerCase().includes(q)
      if (!nameMatch && !setMatch) return false
    }

    return true;
  })
  .sort((a, b) => {
    if (search) {
      const q = search.toLowerCase()
      const scoreDiff = searchScore(a, q) - searchScore(b, q)
      if (scoreDiff !== 0) return scoreDiff
    }
    if (!sortBy) return 0;
    if (sortBy === 'price') {
      const priceA = parseFloat(getPrice(a)) || 0;
      const priceB = parseFloat(getPrice(b)) || 0;
      return sortOrder === 'asc' ? priceA - priceB : priceB - priceA;
    }
    if (sortBy === 'name') {
      const nameA = a.card.name.toLowerCase();
      const nameB = b.card.name.toLowerCase();
      return sortOrder === 'asc' ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
    }
    return 0;
  });

  const paginatedEntries = perPage === 'ALL'
  ? displayedEntries
  : displayedEntries.slice((currentPage - 1) * perPage, currentPage * perPage);

  const totalPages = perPage === 'ALL' ? 1 : Math.ceil(displayedEntries.length / perPage);

  const allOnPageSelected = paginatedEntries.length > 0 && paginatedEntries.every(e => selectedIds.has(e.id));

  const toggleSelectAll = () => {
    if (allOnPageSelected) {
      setSelectedIds(prev => { const next = new Set(prev); paginatedEntries.forEach(e => next.delete(e.id)); return next })
    } else {
      setSelectedIds(prev => { const next = new Set(prev); paginatedEntries.forEach(e => next.add(e.id)); return next })
    }
  };

  return (
    <div>
    <div className="page-header">
    <div>
    <h1>Collection</h1>
    <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
    {entries.length} entries · Est. value{' '}
    <span style={{ color: 'var(--gold)' }}>${totalValue.toFixed(2)}</span>
    </div>
    </div>

    <div className="flex-gap">
    <div style={{ position: 'relative' }}>
      <button ref={colMenuBtnRef} className="btn btn-ghost btn-sm" onClick={openColMenu} title="Choose columns">
        <SlidersHorizontal size={15} />
      </button>
      {showColMenu && (
        <>
          <div style={{ position: 'fixed', inset: 0, zIndex: 99 }} onClick={() => setShowColMenu(false)} />
          <div style={{ position: 'absolute', [colMenuAlign]: 0, top: '110%', zIndex: 100, background: 'var(--surface)',
            border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '0.75rem',
            minWidth: 200, display: 'flex', flexDirection: 'column', gap: '0.5rem', boxShadow: '0 4px 16px rgba(0,0,0,0.4)' }}>
            {[
              ['image',     'Image'],
              ['card',      'Name/Cost/Type'],
              ['set',       'Set'],
              ['qty',       'Quantity'],
              ['condition', 'Condition'],
              ['price',     'Price'],
              ['notes',     'Notes'],
            ].map(([key, label]) => (
              <label key={key} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem' }}>
                <input type="checkbox" checked={visibleCols[key]} onChange={() => toggleCol(key)} style={{ width: 'auto' }} />
                {label}
              </label>
            ))}
          </div>
        </>
      )}
    </div>
    <button className="btn btn-ghost btn-sm" onClick={() => downloadFile('/export/collection/csv', 'collection.csv')}>
    <Download size={15} /> CSV
    </button>
    <button className="btn btn-ghost btn-sm" onClick={() => downloadFile('/export/collection/json', 'collection.json')}>
    <Download size={15} /> JSON
    </button>
    <button className="btn btn-ghost btn-sm" onClick={() => setShowImport(true)}>
    <Upload size={16} /><span className="mobile-hide"> Import</span>
    </button>
    <button className="btn btn-primary btn-sm" onClick={() => setShowAdd(true)}>
    <Plus size={16} /><span className="mobile-hide"> Add Card</span>
    </button>
    </div>
    </div>

    {/* Search Bar */}
    <div className="search-bar">
    <input
    placeholder="Filter by card name or set release…"
    value={search}
    onChange={e => { setSearch(e.target.value); setCurrentPage(1); }}
    />
    </div>

    {isLoading && <div className="loading">Loading collection…</div>}
    {!isLoading && entries.length === 0 && (
      <div className="empty-state">
      <p>Your collection is empty.</p>
      <p>Add cards or use the Quick Add to get started.</p>
      </div>
    )}

    {entries.length > 0 && (
      <>
      {/* Pagination Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
      <div>
      <label>
      Show:&nbsp;
      <select value={perPage} onChange={e => {
        const val = e.target.value === 'ALL' ? 'ALL' : parseInt(e.target.value);
        setPerPage(val);
        setCurrentPage(1);
      }}>
      {[10, 20, 50, 100, 500, 'ALL'].map(size => (
        <option key={size} value={size}>{size}</option>
      ))}
      </select>
      </label>
      </div>

      {perPage !== 'ALL' && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <button className="btn btn-ghost btn-sm" onClick={() => setCurrentPage(p => Math.max(p - 1, 1))} disabled={currentPage === 1}><ChevronLeft size={16} /></button>
          <span style={{ margin: '0 0.25rem', fontSize: '0.875rem' }}>{currentPage} / {totalPages}</span>
          <button className="btn btn-ghost btn-sm" onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))} disabled={currentPage === totalPages}><ChevronRight size={16} /></button>
        </div>
      )}
      </div>

      {/* Filters */}
      <div className="filters" style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', padding: '8px 0', alignItems: 'center' }}>

      {/* Color Filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span>Color:</span>
      {[
        { name: 'Red', hex: '#FF0000' },
        { name: 'White', hex: '#FFFFFF' },
        { name: 'Black', hex: '#000000' },
        { name: 'Green', hex: '#00FF00' },
        { name: 'Blue', hex: '#0000FF' },
      ].map(color => (
        <button
        key={color.name}
        onClick={() =>
          setFilters(f => ({
            ...f,
            colors: f.colors.includes(color.name)
            ? f.colors.filter(c => c !== color.name)
            : [...f.colors, color.name],
          }))
        }
        style={{
          width: 24,
          height: 24,
          borderRadius: '50%',
          border: filters.colors.includes(color.name) ? `2px solid #333` : `1px solid #ccc`,
                      background: color.hex,
                      cursor: 'pointer',
                      padding: 0,
        }}
        />
      ))}
      </div>

      {/* Rarity Filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span>Rarity:</span>
      {[
        { name: 'Common', hex: '#111111' },
        { name: 'Uncommon', hex: '#C0C0C0' },
        { name: 'Rare', hex: '#FFD700' },
        { name: 'Mythic', hex: '#FF8C00' },
      ].map(r => (
        <button
        key={r.name}
        onClick={() =>
          setFilters(f => ({
            ...f,
            rarity: f.rarity.includes(r.name)
            ? f.rarity.filter(x => x !== r.name)
            : [...f.rarity, r.name],
          }))
        }
        style={{
          width: 24,
          height: 24,
          borderRadius: '50%',
          border: filters.rarity.includes(r.name) ? '2px solid #333' : '1px solid #ccc',
                  background: r.hex,
                  cursor: 'pointer',
                  padding: 0,
        }}
        />
      ))}
      </div>

      {onMobile && <div style={{ flexBasis: '100%', height: 0 }} />}

      {/* Foil Filter */}
      <div style={{ display: 'flex', gap: '8px' }}>
      {[
        { label: 'All', value: null },
        { label: 'Foil', value: true },
        { label: 'Non-Foil', value: false }
      ].map(option => {
        const isSelected = filters.foil === option.value;
        return (
          <button
          key={option.label}
          onClick={() => setFilters(f => ({ ...f, foil: option.value }))}
          className="btn btn-ghost btn-sm"
          style={isSelected ? {
            outline: '2px solid #3b82f6',
            outlineOffset: '1px',
            boxShadow: '0 0 6px 1px rgba(59, 130, 246, 0.5)',
            color: '#3b82f6',
          } : {}}
          >
          {option.label}
          </button>
        );
      })}
      </div>

      {/* Favorites Filter */}
      <button
        className="btn btn-ghost btn-sm"
        onClick={() => setFilters(f => ({ ...f, favoritesOnly: !f.favoritesOnly }))}
        style={filters.favoritesOnly ? { color: 'var(--gold)', borderColor: 'var(--gold)' } : {}}
        title="Show favorites only"
      >
        <Star size={14} fill={filters.favoritesOnly ? 'var(--gold)' : 'none'} />
        <span className="mobile-hide"> Favorites</span>
      </button>

      {/* Sort Filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
      <span>Sort</span>
      <select value={sortBy || ''} onChange={e => setSortBy(e.target.value || null)}>
      <option value="">None</option>
      <option value="price">Price</option>
      <option value="name">Name</option>
      </select>
      {sortBy && <button onClick={() => setSortOrder(o => o === 'asc' ? 'desc' : 'asc')}>{sortOrder === 'asc' ? '↑' : '↓'}</button>}
      </div>

      {/* Bulk Action */}
      {selectedIds.size > 0 && (
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{selectedIds.size} selected</span>
          <button className="btn btn-danger btn-sm"
            onClick={() => confirm(`Remove ${selectedIds.size} card(s)?`) && bulkRemove.mutate(selectedIds)}
            disabled={bulkRemove.isPending}>
            <Trash2 size={14} /> {bulkRemove.isPending ? 'Removing…' : 'Remove Selected'}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setSelectedIds(new Set())}>Clear</button>
        </div>
      )}
      </div>

      {/* Table */}
      <table className="table">
      <thead>
      <tr>
      {visibleCols.image     && <th></th>}
      {visibleCols.card      && <th>Card</th>}
      {visibleCols.set       && <th>Set</th>}
      {visibleCols.qty       && <th>Qty</th>}
      {visibleCols.condition && <th>Condition</th>}
      {visibleCols.price     && <th>Price</th>}
      {visibleCols.notes     && <th>Notes</th>}
      <th style={{ textAlign: 'right' }}>
        <input type="checkbox" checked={allOnPageSelected} onChange={toggleSelectAll} style={{ width: 'auto', cursor: 'pointer' }} />
      </th>
      </tr>
      </thead>
      <tbody>
      {paginatedEntries.map(entry => (
        <tr key={entry.id}>
        {visibleCols.image && (
          <td style={{ width: 40 }}>
          {entry.card.image_uri && (
            <img src={entry.card.image_uri} alt={entry.card.name}
              style={{ width: 36, borderRadius: 4, cursor: 'pointer' }}
              onClick={() => setViewingCard(entry.card)} />
          )}
          </td>
        )}
        {visibleCols.card && (
          <td>
          <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{entry.card.name}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {entry.card.mana_cost} · {entry.card.type_line}
          </div>
          </td>
        )}
        {visibleCols.set && (
          <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          {entry.card.set_name}<br />#{entry.card.collector_number}
          </td>
        )}
        {visibleCols.qty       && <td>{entry.quantity}</td>}
        {visibleCols.condition && (
          <td>
          <span className={`badge badge-${entry.condition.toLowerCase()}`}>{entry.condition}</span>
          {entry.foil && <span className="badge badge-foil" style={{ marginLeft: 4 }}>Foil</span>}
          </td>
        )}
        {visibleCols.price && (
          <td style={{ color: getPriceColor(entry), fontWeight: 600 }}>
          {getPrice(entry) ? (
            <>
            ${getPrice(entry)}
            {entry.condition !== 'NM' && (
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
              {entry.condition} adj.
              </div>
            )}
            {entry.foil && entry.card.price_usd_foil && (
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>foil</div>
            )}
            </>
          ) : '—'}
          </td>
        )}
        {visibleCols.notes && (
          <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: 140 }}>{entry.notes}</td>
        )}
        <td>
        <div className="flex-gap" style={{ justifyContent: 'flex-end' }}>
        {onMobile ? (
          <div style={{ position: 'relative' }}>
            <button className="btn btn-ghost btn-sm"
              onClick={() => setOpenMenuId(openMenuId === entry.id ? null : entry.id)}>
              <MoreVertical size={14} />
            </button>
            {openMenuId === entry.id && (
              <>
                <div style={{ position: 'fixed', inset: 0, zIndex: 99 }} onClick={() => setOpenMenuId(null)} />
                <div style={{ position: 'absolute', right: 0, top: '110%', zIndex: 100,
                  background: 'var(--surface)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)', overflow: 'hidden', minWidth: 140,
                  boxShadow: '0 4px 16px rgba(0,0,0,0.4)' }}>
                  <button className="btn btn-ghost" style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0, color: entry.is_favorite ? 'var(--gold)' : undefined }}
                    onClick={() => { toggleFavorite.mutate(entry); setOpenMenuId(null); }}>
                    <Star size={14} fill={entry.is_favorite ? 'var(--gold)' : 'none'} />
                    {entry.is_favorite ? 'Unfavorite' : 'Favorite'}
                  </button>
                  <button className="btn btn-ghost" style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0 }}
                    onClick={() => { setEditing(entry); setOpenMenuId(null); }}>
                    <Pencil size={14} /> Edit
                  </button>
                  <button className="btn btn-danger" style={{ width: '100%', justifyContent: 'flex-start', borderRadius: 0 }}
                    onClick={() => { if (confirm('Remove this card?')) { remove.mutate(entry.id); setOpenMenuId(null); } }}>
                    <Trash2 size={14} /> Delete
                  </button>
                </div>
              </>
            )}
          </div>
        ) : (
          <>
            <button className="btn btn-ghost btn-sm" onClick={() => toggleFavorite.mutate(entry)}
              title={entry.is_favorite ? 'Remove from favorites' : 'Add to favorites'}
              style={{ color: entry.is_favorite ? 'var(--gold)' : undefined }}>
              <Star size={14} fill={entry.is_favorite ? 'var(--gold)' : 'none'} />
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => setEditing(entry)}><Pencil size={14} /></button>
            <button className="btn btn-danger btn-sm" onClick={() => confirm('Remove this card?') && remove.mutate(entry.id)}><Trash2 size={14} /></button>
          </>
        )}
        <input type="checkbox" checked={selectedIds.has(entry.id)} onChange={() => toggleSelect(entry.id)} style={{ width: 'auto', cursor: 'pointer' }} />
        </div>
        </td>
        </tr>
      ))}
      </tbody>
      </table>
      </>
    )}

    {showAdd && <AddCardModal onClose={() => setShowAdd(false)} />}
    {editing && <EditModal entry={editing} onClose={() => setEditing(null)} />}
    {showImport && <ImportModal onClose={() => setShowImport(false)} />}
    {viewingCard && <CardImageModal card={viewingCard} onClose={() => setViewingCard(null)} />}
    </div>
  );
}

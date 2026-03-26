import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Pencil, Trash2, Download, Upload } from 'lucide-react'
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

export default function Collection() {

  useEffect(() => { document.title = 'Collection - OpenMTG' }, [])

  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [editing, setEditing] = useState(null);

  const [sortBy, setSortBy] = useState(null);
  const [sortOrder, setSortOrder] = useState('asc');

  const [filters, setFilters] = useState({
    colors: [],
    sets: [],
    foil: null,
    rarity: [],
  });

  const [perPage, setPerPage] = useState(20);
  const [currentPage, setCurrentPage] = useState(1);

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['collection', search],
    queryFn: () => api.get(`/collection${search ? `?search=${search}` : ''}`).then(r => r.data),
  });

  const remove = useMutation({
    mutationFn: (id) => api.delete(`/collection/${id}`),
                             onSuccess: () => qc.invalidateQueries(['collection']),
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

  let displayedEntries = entries
  .filter(entry => {
    const cardColors = getCardCastingColors(entry.card);

    if (filters.colors.length > 0) {
      const selectedColors = filters.colors.map(fc => COLOR_CODES[fc]);
      if (!cardColors.some(c => selectedColors.includes(c))) return false;
    }

    if (filters.sets.length > 0 && !entry.card.set_name.toLowerCase().includes(filters.sets[0].toLowerCase())) return false;

    if (filters.foil !== null && entry.foil !== filters.foil) return false;

    if (filters.rarity.length > 0 && !filters.rarity.map(r => r.toLowerCase()).includes(entry.card.rarity)) return false;

    if (search && !entry.card.name.toLowerCase().includes(search.toLowerCase())) return false;

    return true;
  })
  .sort((a, b) => {
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
    <button className="btn btn-ghost btn-sm" onClick={() => downloadFile('/export/collection/csv', 'collection.csv')}>
    <Download size={15} /> CSV
    </button>
    <button className="btn btn-ghost btn-sm" onClick={() => downloadFile('/export/collection/json', 'collection.json')}>
    <Download size={15} /> JSON
    </button>
    <button className="btn btn-ghost" onClick={() => setShowImport(true)}>
    <Upload size={18} /> Import
    </button>
    <button className="btn btn-primary" onClick={() => setShowAdd(true)}>
    <Plus size={18} /> Add Card
    </button>
    </div>
    </div>

    {/* Search Bar */}
    <div className="search-bar">
    <input
    placeholder="Filter by name…"
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
        <div>
        <button onClick={() => setCurrentPage(p => Math.max(p - 1, 1))} disabled={currentPage === 1}>Prev</button>
        <span style={{ margin: '0 0.5rem' }}>{currentPage} / {totalPages}</span>
        <button onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))} disabled={currentPage === totalPages}>Next</button>
        </div>
      )}
      </div>

      {/* Filters */}
      <div className="filters" style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', padding: '8px 0' }}>

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

      {/* Set Filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
      <span>Set:</span>
      <input
      type="text"
      placeholder="Filter set"
      value={filters.sets[0] || ''}
      onChange={e => setFilters(f => ({ ...f, sets: e.target.value ? [e.target.value] : [] }))}
      style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid #ccc' }}
      />
      </div>

      {/* Foil Filter */}
      <div style={{ display: 'flex', gap: '8px' }}>
      {[
        { label: 'All', value: null },
        { label: 'Only Foils', value: true },
        { label: 'Only Non-Foils', value: false }
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

      {/* Rarity Filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
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

      {/* Sort Filter */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
      <span>Sort by:</span>
      <select value={sortBy || ''} onChange={e => setSortBy(e.target.value || null)}>
      <option value="">None</option>
      <option value="price">Price</option>
      <option value="name">Name</option>
      </select>
      {sortBy && <button onClick={() => setSortOrder(o => o === 'asc' ? 'desc' : 'asc')}>{sortOrder === 'asc' ? '↑' : '↓'}</button>}
      </div>
      </div>

      {/* Table */}
      <table className="table">
      <thead>
      <tr>
      <th></th>
      <th>Card</th>
      <th>Set</th>
      <th>Qty</th>
      <th>Condition</th>
      <th>Price</th>
      <th>Notes</th>
      <th></th>
      </tr>
      </thead>
      <tbody>
      {paginatedEntries.map(entry => (
        <tr key={entry.id}>
        <td style={{ width: 40 }}>
        {entry.card.image_uri && <img src={entry.card.image_uri} alt={entry.card.name} style={{ width: 36, borderRadius: 4 }} />}
        </td>
        <td>
        <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{entry.card.name}</div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
        {entry.card.mana_cost} · {entry.card.type_line}
        </div>
        </td>
        <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        {entry.card.set_name}<br />#{entry.card.collector_number}
        </td>
        <td>{entry.quantity}</td>
        <td>
        <span className={`badge badge-${entry.condition.toLowerCase()}`}>{entry.condition}</span>
        {entry.foil && <span className="badge badge-foil" style={{ marginLeft: 4 }}>Foil</span>}
        </td>
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
        <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: 140 }}>{entry.notes}</td>
        <td>
        <div className="flex-gap">
        <button className="btn btn-ghost btn-sm" onClick={() => setEditing(entry)}><Pencil size={14} /></button>
        <button className="btn btn-danger btn-sm" onClick={() => confirm('Remove this card?') && remove.mutate(entry.id)}><Trash2 size={14} /></button>
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
    </div>
  );
}

import { useQuery } from '@tanstack/react-query'
import { Library, DollarSign, Layers, Sparkles } from 'lucide-react'
import api from '../api'

const RARITY_COLORS = {
  common:   '#9aa0a6',
  uncommon: '#70b0f0',
  rare:     '#f0c060',
  mythic:   '#f08030',
  special:  '#c09af0',
  bonus:    '#c09af0',
  unknown:  '#555',
}

const COLOR_MAP = {
  White:     '#f9f6ee',
  Blue:      '#4a90d9',
  Black:     '#b08ec0',
  Red:       '#e05c5c',
  Green:     '#4caf7d',
  Colorless: '#9aa0a6',
}

const TYPE_COLORS = [
  '#7c6af7','#4a90d9','#e05c5c','#4caf7d',
  '#f0c060','#c09af0','#f08030','#9aa0a6',
]

const CONDITION_COLORS = {
  NM:  '#4caf7d',
  LP:  '#f0c060',
  MP:  '#f08030',
  HP:  '#e05c5c',
  DMG: '#6b4e71',
}

function StatTile({ icon, label, value, sub, accent }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius)', padding: '1.25rem 1.5rem',
      borderTop: `3px solid ${accent || 'var(--accent)'}` }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)',
          textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
        <span style={{ color: accent || 'var(--accent)', opacity: 0.7 }}>{icon}</span>
      </div>
      <div style={{ fontSize: '1.75rem', fontWeight: 700, lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>{sub}</div>}
    </div>
  )
}

function BarChart({ data, colorKey, valueKey = 'count', labelKey = 'name', showValue = true }) {
  const max = Math.max(...data.map(d => d[valueKey]), 1)
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      {data.map((item, i) => (
        <div key={item[labelKey]}>
          <div style={{ display: 'flex', justifyContent: 'space-between',
            fontSize: '0.8rem', marginBottom: '0.25rem' }}>
            <span style={{ color: 'var(--text)', fontWeight: 500 }}>{item[labelKey]}</span>
            {showValue && (
              <span style={{ color: 'var(--text-muted)' }}>
                {item[valueKey].toLocaleString()}
                {item.value !== undefined &&
                  <span style={{ color: 'var(--gold)', marginLeft: '0.5rem' }}>
                    ${item.value.toFixed(2)}
                  </span>}
              </span>
            )}
          </div>
          <div style={{ background: 'var(--surface2)', borderRadius: 4, height: 8, overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 4,
              width: `${(item[valueKey] / max) * 100}%`,
              background: colorKey
                ? (colorKey[item[labelKey]] || TYPE_COLORS[i % TYPE_COLORS.length])
                : TYPE_COLORS[i % TYPE_COLORS.length],
              transition: 'width 0.6s ease',
            }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function DonutChart({ data, colorKey, size = 160 }) {
  const total = data.reduce((s, d) => s + d.count, 0)
  if (total === 0) return null

  const r = 60, cx = size / 2, cy = size / 2
  const strokeWidth = 20
  const circumference = 2 * Math.PI * r
  const gap = 0.02  // fraction of circle to leave as gap between segments

  let cumulative = 0
  const segments = data.map((d, i) => {
    const pct = d.count / total
    const seg = {
      ...d,
      pct,
      start: cumulative,
      color: colorKey?.[d.name] || TYPE_COLORS[i % TYPE_COLORS.length],
    }
    cumulative += pct
    return seg
  })

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
      <svg width={size} height={size} style={{ flexShrink: 0 }}>
        {/* Background track */}
        <circle cx={cx} cy={cy} r={r} fill="none"
          stroke="var(--surface2)" strokeWidth={strokeWidth} />
        {segments.map((seg, i) => {
          // Leave a small gap between segments by reducing dash length
          const dashLen = Math.max(0, (seg.pct - gap) * circumference)
          // Rotate so each segment starts at the right position
          // -90 deg puts the start at 12 o'clock instead of 3 o'clock
          const rotateDeg = (seg.start * 360) - 90
          return (
            <circle key={i}
              cx={cx} cy={cy} r={r}
              fill="none"
              stroke={seg.color}
              strokeWidth={strokeWidth}
              strokeDasharray={`${dashLen} ${circumference}`}
              strokeDashoffset={0}
              transform={`rotate(${rotateDeg} ${cx} ${cy})`}
            />
          )
        })}
        <text x={cx} y={cy - 6} textAnchor="middle"
          style={{ fill: 'var(--text)', fontSize: 14, fontWeight: 700 }}>
          {total.toLocaleString()}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle"
          style={{ fill: 'var(--text-muted)', fontSize: 10 }}>
          cards
        </text>
      </svg>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', flex: 1 }}>
        {segments.map(seg => (
          <div key={seg.name} style={{ display: 'flex', alignItems: 'center',
            gap: '0.5rem', fontSize: '0.8rem' }}>
            <div style={{ width: 10, height: 10, borderRadius: '50%',
              background: seg.color, flexShrink: 0 }} />
            <span style={{ flex: 1, color: 'var(--text)' }}>{seg.name}</span>
            <span style={{ color: 'var(--text-muted)' }}>{seg.count.toLocaleString()}</span>
            <span style={{ color: 'var(--text-muted)', width: 36, textAlign: 'right' }}>
              {(seg.pct * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function Card({ title, children }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius)', padding: '1.25rem' }}>
      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-muted)',
        textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem' }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function SetIcon({ setCode, size = 18 }) {
  return (
    <img
      src={`https://svgs.scryfall.io/sets/${setCode}.svg`}
      alt={setCode}
      width={size} height={size}
      onError={e => e.target.style.display = 'none'}
      style={{ filter: 'invert(1) sepia(1) saturate(0) brightness(1.5)',
        objectFit: 'contain', flexShrink: 0 }}
    />
  )
}

export default function Stats() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get('/collection/stats').then(r => r.data),
  })

  if (isLoading) return <div className="loading">Calculating stats…</div>

  if (!stats || !stats.summary) return (
    <div className="empty-state">
      <p>No collection data yet.</p>
      <p>Add some cards to see your stats.</p>
    </div>
  )

  const { summary, rarity, colors, types, conditions, top_cards, top_sets } = stats

  return (
    <div>
      <div className="page-header">
        <h1>Collection Stats</h1>
      </div>

      {/* Summary tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: '1rem', marginBottom: '1.5rem' }}>
        <StatTile icon={<Library size={18} />} label="Total Cards"
          value={summary.total_cards.toLocaleString()}
          sub={`${summary.unique_cards.toLocaleString()} unique`}
          accent="var(--accent)" />
        <StatTile icon={<DollarSign size={18} />} label="Est. Total Value"
          value={`$${summary.total_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          sub={`Avg $${(summary.total_value / summary.total_cards).toFixed(2)} per card`}
          accent="var(--gold)" />
        <StatTile icon={<Layers size={18} />} label="Sets Represented"
          value={summary.sets_represented.toLocaleString()}
          accent="#4a90d9" />
        <StatTile icon={<Sparkles size={18} />} label="Foils"
          value={summary.foil_count.toLocaleString()}
          sub={`$${summary.foil_value.toFixed(2)} foil value`}
          accent="#c09af0" />
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '1rem', marginBottom: '1rem' }}>
        <Card title="By Rarity">
          <BarChart data={rarity} colorKey={RARITY_COLORS} />
        </Card>
        <Card title="By Color Identity">
          {colors.length > 0
            ? <DonutChart data={colors} colorKey={COLOR_MAP} />
            : <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No data</p>}
        </Card>
        <Card title="By Card Type">
          <BarChart data={types} colorKey={null} />
        </Card>
      </div>

      {/* Second row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem',
        marginBottom: '1rem' }}>
        <Card title="By Condition">
          <BarChart data={conditions} colorKey={CONDITION_COLORS} valueKey="count" />
        </Card>
        <Card title="Top Sets">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {top_sets.map(s => (
              <div key={s.set_code} style={{ display: 'flex', alignItems: 'center',
                gap: '0.6rem', fontSize: '0.875rem' }}>
                <SetIcon setCode={s.set_code} size={20} />
                <span style={{ flex: 1, color: 'var(--text)' }}>{s.set_name}</span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {s.count.toLocaleString()} cards
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Foil vs Normal */}
      <div style={{ marginBottom: '1rem' }}>
        <Card title="Foil vs Normal">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <DonutChart
                data={[
                  { name: 'Normal', count: summary.normal_count },
                  { name: 'Foil',   count: summary.foil_count },
                ]}
                colorKey={{ Normal: '#4a90d9', Foil: '#c09af0' }}
                size={140}
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center',
              gap: '0.75rem' }}>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Normal Value</div>
                <div style={{ fontWeight: 700, color: '#4a90d9' }}>
                  ${summary.normal_value.toFixed(2)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Foil Value</div>
                <div style={{ fontWeight: 700, color: '#c09af0' }}>
                  ${summary.foil_value.toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Top 10 most valuable */}
      <Card title="Top 10 Most Valuable Cards">
        <table className="table">
          <thead>
            <tr>
              <th></th>
              <th>Card</th>
              <th>Set</th>
              <th>Condition</th>
              <th>Qty</th>
              <th>Price ea.</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {top_cards.map((c, i) => (
              <tr key={i}>
                <td style={{ width: 40 }}>
                  {c.image_uri &&
                    <img src={c.image_uri} alt={c.name}
                      style={{ width: 36, borderRadius: 4 }} />}
                </td>
                <td>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{c.name}</div>
                  {c.foil && <span className="badge badge-foil">Foil</span>}
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <SetIcon setCode={c.set_code} size={16} />
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {c.set_name}
                    </span>
                  </div>
                </td>
                <td>
                  <span className={`badge badge-${c.condition.toLowerCase()}`}>
                    {c.condition}
                  </span>
                </td>
                <td>{c.quantity}</td>
                <td style={{ color: 'var(--gold)' }}>
                  {c.price_usd ? `$${c.price_usd}` : '—'}
                </td>
                <td style={{ color: 'var(--gold)', fontWeight: 700 }}>
                  ${c.total_value.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}

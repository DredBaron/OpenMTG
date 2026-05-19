import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Library, DollarSign, Layers, Sparkles } from 'lucide-react'
import api from '../api'
import { useIsMobile } from '../hooks/useIsMobile'
import { useCurrency } from '../hooks/useCurrency'
import { formatPrice } from '../utils/currency'

const RARITY_COLORS = {
  common:   '#9aa0a6',
  uncommon: '#70b0f0',
  rare:     '#f0c060',
  mythic:   '#f08030',
  special:  'var(--foil)',
  bonus:    'var(--foil)',
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
  'var(--accent)','var(--info)','#e05c5c','#4caf7d',
  '#f0c060','var(--foil)','#f08030','#9aa0a6',
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
    <div className="stat-tile" style={{ '--tile-accent': accent }}>
      <div className="stat-tile-header">
        <span className="stat-tile-label">{label}</span>
        <span className="stat-tile-icon" style={{ color: accent || 'var(--accent)' }}>{icon}</span>
      </div>
      <div className="stat-tile-value">{value}</div>
      {sub && <div className="stat-tile-sub">{sub}</div>}
    </div>
  )
}

function BarChart({ data, colorKey, valueKey = 'count', labelKey = 'name', showValue = true, currency = 'usd', market }) {
  const max = Math.max(...data.map(d => d[valueKey]), 1)
  return (
    <div className="bar-chart-col">
      {data.map((item, i) => (
        <div key={item[labelKey]}>
          <div className="bar-row-labels">
            <span className="bar-row-name">{item[labelKey]}</span>
            {showValue && (
              <span style={{ color: 'var(--text-muted)' }}>
                {item[valueKey].toLocaleString()}
                {item.value !== undefined &&
                  <span className="text-gold" style={{ marginLeft: '0.5rem' }}>
                    {formatPrice(item.value, currency, market)}
                  </span>}
              </span>
            )}
          </div>
          <div className="bar-track">
            <div className="bar-fill" style={{
              '--bar-w': `${(item[valueKey] / max) * 100}%`,
              '--bar-bg': colorKey
                ? (colorKey[item[labelKey]] || TYPE_COLORS[i % TYPE_COLORS.length])
                : TYPE_COLORS[i % TYPE_COLORS.length],
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

  const GAP_PX = 4
  const MIN_SLICE_PX = 6

  const colored = data
    .map((d, i) => ({ ...d, color: colorKey?.[d.name] || TYPE_COLORS[i % TYPE_COLORS.length] }))
    .filter(d => d.count > 0)

  const N = colored.length
  const totalDataPx = circumference - N * GAP_PX

  const sized = colored.map(d => ({
    ...d,
    slicePx: Math.max(MIN_SLICE_PX, (d.count / total) * totalDataPx),
  }))

  const overflow = sized.reduce((s, d) => s + d.slicePx, 0) - totalDataPx
  if (overflow > 0) {
    const largest = sized.reduce((a, b) => a.slicePx > b.slicePx ? a : b)
    largest.slicePx = Math.max(MIN_SLICE_PX, largest.slicePx - overflow)
  }

  const segments = sized.reduce((acc, d) => {
    const startPx = acc.cumPx
    acc.segments.push({ ...d, startPx })
    acc.cumPx += d.slicePx + GAP_PX
    return acc
  }, { cumPx: 0, segments: [] }).segments

  return (
    <div className="donut-wrap">
      <svg width={size} height={size} style={{ flexShrink: 0 }}>
        <circle cx={cx} cy={cy} r={r} fill="none"
          stroke="var(--surface2)" strokeWidth={strokeWidth} />
        {segments.map((seg, i) => {
          const rotateDeg = (seg.startPx / circumference) * 360 - 90
          return (
            <circle key={i}
              cx={cx} cy={cy} r={r}
              fill="none"
              stroke={seg.color}
              strokeWidth={strokeWidth}
              strokeDasharray={`${seg.slicePx} ${circumference}`}
              strokeDashoffset={0}
              transform={`rotate(${rotateDeg} ${cx} ${cy})`}
            />
          )
        })}
        <text x={cx} y={cy - 6} textAnchor="middle" className="donut-total-text">
          {total.toLocaleString()}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" className="donut-cards-text">
          cards
        </text>
      </svg>
      <div className="donut-legend">
        {segments.map(seg => (
          <div key={seg.name} className="donut-legend-item">
            <div className="donut-dot" style={{ background: seg.color }} />
            <span className="donut-name">{seg.name}</span>
            <span style={{ color: 'var(--text-muted)' }}>{seg.count.toLocaleString()}</span>
            <span className="donut-pct">
              {((seg.count / total) * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatCard({ title, children }) {
  return (
    <div className="stat-card">
      <div className="stat-card-title">{title}</div>
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
      className="set-icon"
    />
  )
}

export default function Stats() {

  useEffect(() => { document.title = 'Stats - OpenMTG' }, [])

  const isMobile = useIsMobile()
  const { currency, market } = useCurrency()

  const { data: stats, isLoading } = useQuery({
    queryKey: ['stats'],
    queryFn: () => api.get('/collection/stats').then(r => r.data),
  })

  if (isLoading) return <div className="loading">Calculating stats</div>

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

      <div className="stats-grid-4">
        <StatTile icon={<Library size={18} />} label="Total Cards"
          value={summary.total_cards.toLocaleString()}
          sub={`${summary.unique_cards.toLocaleString()} unique`}
          accent="var(--accent)" />
        <StatTile icon={<DollarSign size={18} />} label="Est. Total Value"
          value={formatPrice(summary.total_value, currency, market)}
          sub={`Avg ${formatPrice(summary.total_value / summary.total_cards, currency, market)} per card`}
          accent="var(--gold)" />
        <StatTile icon={<Layers size={18} />} label="Sets Represented"
          value={summary.sets_represented.toLocaleString()}
          accent="var(--info)" />
        <StatTile icon={<Sparkles size={18} />} label="Foils"
          value={summary.foil_count.toLocaleString()}
          sub={`${formatPrice(summary.foil_value, currency, market)} foil value`}
          accent="var(--foil)" />
      </div>

      <div className="stats-grid-3">
        <StatCard title="By Rarity">
          <BarChart data={rarity} colorKey={RARITY_COLORS} currency={currency} market={market} />
        </StatCard>
        <StatCard title="By Color Identity">
          {colors.length > 0
            ? <DonutChart data={colors} colorKey={COLOR_MAP} currency={currency} />
            : <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No data</p>}
        </StatCard>
        <StatCard title="By Card Type">
          <BarChart data={types} colorKey={null} />
        </StatCard>
      </div>

      <div className="stats-grid-2">
        <StatCard title="By Condition">
          <BarChart data={conditions} colorKey={CONDITION_COLORS} valueKey="count" currency={currency} market={market} />
        </StatCard>
        <StatCard title="Top Sets">
          <div className="top-sets-list">
            {top_sets.map(s => (
              <div key={s.set_code} className="top-set-item">
                <SetIcon setCode={s.set_code} size={20} />
                <span className="top-set-name">{s.set_name}</span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {s.count.toLocaleString()} cards
                </span>
              </div>
            ))}
          </div>
        </StatCard>
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <StatCard title="Foil vs Normal">
          <div className="foil-split-grid">
            <div>
              <DonutChart
                data={[
                  { name: 'Normal', count: summary.normal_count },
                  { name: 'Foil',   count: summary.foil_count },
                ]}
                colorKey={{ Normal: 'var(--info)', Foil: 'var(--foil)' }}
                size={140}
              />
            </div>
            <div className="foil-value-col">
              <div>
                <div className="text-muted-sm">Normal Value</div>
                <div className="foil-split-value" style={{ color: 'var(--info)' }}>
                  {formatPrice(summary.normal_value, currency, market)}
                </div>
              </div>
              <div>
                <div className="text-muted-sm">Foil Value</div>
                <div className="foil-split-value" style={{ color: 'var(--foil)' }}>
                  {formatPrice(summary.foil_value, currency, market)}
                </div>
              </div>
            </div>
          </div>
        </StatCard>
      </div>

      <StatCard title="Top 10 Most Valuable Cards">
        {isMobile ? (
          <div>
            {top_cards.map((c, i) => (
              <div key={i} className="top-card-mobile-row">
                {c.image_uri &&
                  <img src={c.image_uri} alt={c.name} className="top-card-img" />}
                <div className="top-card-body">
                  <div className="top-card-header">
                    <div className="top-card-name-wrap">
                      <div className="top-card-name-cell">{c.name}</div>
                      {c.foil && <span className="badge badge-foil">Foil</span>}
                    </div>
                    <div className="top-card-total">
                      {formatPrice(c.total_value, currency, market)}
                    </div>
                  </div>
                  <div className="top-card-meta-row">
                    <SetIcon setCode={c.set_code} size={14} />
                    <span className="top-card-set-name">{c.set_name}</span>
                    <span className={`badge badge-${c.condition.toLowerCase()}`}>{c.condition}</span>
                    <span className="text-muted-sm">x{c.quantity}</span>
                    {c.price != null &&
                      <span className="top-card-ea">
                        {formatPrice(c.price, currency, market)} ea.
                      </span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
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
                      <img src={c.image_uri} alt={c.name} className="top-card-table-img" />}
                  </td>
                  <td>
                    <div className="top-card-name-cell">{c.name}</div>
                    {c.foil && <span className="badge badge-foil">Foil</span>}
                  </td>
                  <td>
                    <div className="top-card-set-cell">
                      <SetIcon setCode={c.set_code} size={16} />
                      <span className="text-muted-sm">{c.set_name}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`badge badge-${c.condition.toLowerCase()}`}>
                      {c.condition}
                    </span>
                  </td>
                  <td>{c.quantity}</td>
                  <td style={{ color: 'var(--gold)' }}>
                    {c.price != null ? formatPrice(c.price, currency, market) : '-'}
                  </td>
                  <td className="top-card-total">
                    {formatPrice(c.total_value, currency, market)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </StatCard>
    </div>
  )
}

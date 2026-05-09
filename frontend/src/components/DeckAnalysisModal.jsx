const COLOR_LABELS = { W: 'White', U: 'Blue', B: 'Black', R: 'Red', G: 'Green', C: 'Colorless' }
const COLOR_HEX    = { W: '#f5f0d8', U: '#1a6fb0', B: '#6b5fa5', R: '#d63c2a', G: '#2a8a4a', C: '#8888a0' }
const RARITY_COLOR = { common: '#909090', uncommon: '#78b0c8', rare: '#d4a843', mythic: '#e87030' }
const TYPE_ORDER   = ['Creature', 'Instant', 'Sorcery', 'Enchantment', 'Artifact', 'Planeswalker', 'Land', 'Other']

function parseCMC(manaCost) {
    if (!manaCost) return 0
        let cmc = 0
        for (const m of (manaCost.match(/\{([^}]+)\}/g) || [])) {
            const inner = m.slice(1, -1)
            const num = parseInt(inner)
            if (!isNaN(num)) cmc += num
                else if (!['X', 'Y', 'Z'].includes(inner)) cmc += 1
        }
        return cmc
        }

        function getCardType(typeLine) {
            if (!typeLine) return 'Other'
                for (const t of TYPE_ORDER) {
                    if (t !== 'Other' && typeLine.includes(t)) return t
                }
                return 'Other'
        }

        function BarChart({ data }) {
            const max = Math.max(...data.map(d => d.value), 1)
            return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                {data.map(({ label, value, color }) => (
                    <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <div style={{ width: 88, fontSize: '0.75rem', color: 'var(--text-muted)',
                        textAlign: 'right', flexShrink: 0 }}>
                        {label}
                        </div>
                        <div style={{ flex: 1, background: 'var(--surface2)', borderRadius: 3,
                            height: 14, overflow: 'hidden' }}>
                            <div style={{
                                width: `${(value / max) * 100}%`,
                                                        background: color ?? 'var(--accent)',
                                                        height: '100%',
                                                        borderRadius: 3,
                                                        minWidth: value > 0 ? 4 : 0,
                            }} />
                            </div>
                            <div style={{ width: 24, fontSize: '0.75rem', color: 'var(--text-muted)', flexShrink: 0 }}>
                            {value}
                            </div>
                            </div>
                ))}
                </div>
            )
        }

        function Section({ title, children }) {
            return (
                <div style={{ marginBottom: '1.5rem' }}>
                <div className="section-label">{title}</div>
                {children}
                </div>
            )
        }

        export default function DeckAnalysisModal({ deck, onClose }) {
            const mainCards = deck.cards.filter(c => !c.is_sideboard)

            const curveBuckets = {}
            for (const dc of mainCards) {
                if (dc.card.type_line?.includes('Land')) continue
                    const cmc = parseCMC(dc.card.mana_cost)
                    const key = cmc >= 7 ? '7+' : String(cmc)
                    curveBuckets[key] = (curveBuckets[key] ?? 0) + dc.quantity
            }
            const curveData = ['0','1','2','3','4','5','6','7+'].map(k => ({
                label: k, value: curveBuckets[k] ?? 0,
            }))

            let cmcTotal = 0, cmcCount = 0
            for (const dc of mainCards) {
                if (dc.card.type_line?.includes('Land')) continue
                    cmcTotal += parseCMC(dc.card.mana_cost) * dc.quantity
                    cmcCount += dc.quantity
            }
            const avgCMC = cmcCount > 0 ? (cmcTotal / cmcCount).toFixed(2) : '—'

            const colorCounts = { W: 0, U: 0, B: 0, R: 0, G: 0, C: 0 }
            for (const dc of mainCards) {
                const colors = dc.card.colors ?? []
                if (colors.length === 0) { colorCounts.C += dc.quantity; continue }
                for (const c of colors) if (c in colorCounts) colorCounts[c] += dc.quantity
            }
            const colorData = Object.entries(colorCounts)
            .filter(([, v]) => v > 0)
            .map(([k, v]) => ({ label: COLOR_LABELS[k] ?? k, value: v, color: COLOR_HEX[k] }))

            const typeCounts = Object.fromEntries(TYPE_ORDER.map(t => [t, 0]))
            for (const dc of mainCards) {
                typeCounts[getCardType(dc.card.type_line)] += dc.quantity
            }
            const typeData = TYPE_ORDER
            .filter(t => typeCounts[t] > 0)
            .map(t => ({ label: t, value: typeCounts[t] }))

            const rarityCounts = { common: 0, uncommon: 0, rare: 0, mythic: 0 }
            for (const dc of mainCards) {
                const r = dc.card.rarity?.toLowerCase()
                if (r in rarityCounts) rarityCounts[r] += dc.quantity
            }
            const rarityData = Object.entries(rarityCounts)
            .filter(([, v]) => v > 0)
            .map(([k, v]) => ({
                label: k.charAt(0).toUpperCase() + k.slice(1),
                              value: v,
                              color: RARITY_COLOR[k],
            }))

            return (
                <div className="modal-overlay" onClick={onClose}>
                <div className="modal" style={{ maxWidth: 460 }} onClick={e => e.stopPropagation()}>
                <h2>Deck Analysis</h2>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
                {deck.name}
                {deck.format && <span style={{ textTransform: 'capitalize' }}> · {deck.format}</span>}
                {' · '}Avg. CMC: <strong style={{ color: 'var(--text)' }}>{avgCMC}</strong>
                </div>

                <Section title="Mana Curve">
                <BarChart data={curveData} />
                </Section>

                {colorData.length > 0 && (
                    <Section title="Color Distribution">
                    <BarChart data={colorData} />
                    </Section>
                )}

                <Section title="Card Types">
                <BarChart data={typeData} />
                </Section>

                {rarityData.length > 0 && (
                    <Section title="Rarity">
                    <BarChart data={rarityData} />
                    </Section>
                )}

                <div className="modal-footer">
                <button className="btn btn-ghost" onClick={onClose}>Close</button>
                </div>
                </div>
                </div>
            )
        }

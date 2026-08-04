import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, Navigate } from 'react-router-dom'
import { Plus, ArrowLeftRight } from 'lucide-react'
import api from '../api'
import TradeAddCardModal from '../components/TradeAddCardModal'
import { useAuth } from '../hooks/useAuth'

const STATUS_LABEL = {
  proposed:    'Proposed',
  active:      'Negotiating',
  accepted:    'Accepted',
  rejected:    'Rejected',
  cancelled:   'Cancelled',
}

const STATUS_COLOR = {
  proposed:    'var(--accent)',
  active:      'var(--info)',
  accepted:    'var(--success)',
  rejected:    'var(--danger)',
  cancelled:   'var(--text-muted)',
}

export default function Trades() {
  useEffect(() => { document.title = 'Trades - OpenMTG' }, [])

  const { tradesEnabled } = useAuth()
  const qc = useQueryClient()
  const navigate = useNavigate()

  if (!tradesEnabled) return <Navigate to="/collection" replace />
  const [showPropose, setShowPropose] = useState(false)
  const [proposeUsername, setProposeUsername] = useState('')
  const [proposeItems, setProposeItems] = useState([])
  const [showAddCard, setShowAddCard] = useState(false)
  const [proposeError, setProposeError] = useState('')

  const { data: trades = [], isLoading } = useQuery({
    queryKey: ['trades'],
    queryFn: () => api.get('/trades').then(r => r.data),
  })

  const propose = useMutation({
    mutationFn: () => api.post('/trades', {
      counterpart_username: proposeUsername.trim(),
      items: proposeItems.map(i => ({ collection_entry_id: i.id, quantity: i.tradeQty })),
    }),
    onSuccess: (res) => {
      qc.invalidateQueries(['trades'])
      qc.invalidateQueries(['trades-pending'])
      setShowPropose(false)
      setProposeUsername('')
      setProposeItems([])
      navigate(`/trades/${res.data.id}`)
    },
    onError: (err) => {
      setProposeError(err.response?.data?.detail || 'Could not propose trade')
    },
  })

  const active = trades.filter(t => ['proposed', 'active'].includes(t.status))
  const history = trades.filter(t => !['proposed', 'active'].includes(t.status))

  const removeProposedItem = (id) => setProposeItems(prev => prev.filter(i => i.id !== id))

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Trades</h1>
          <div className="page-subtitle">{active.length} active</div>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setShowPropose(true)}>
          <Plus size={15} /> Propose Trade
        </button>
      </div>

      {isLoading && <div className="loading">Loading trades</div>}

      {!isLoading && active.length === 0 && history.length === 0 && (
        <div className="empty-state">
          <p>No trades yet. Propose one to get started.</p>
        </div>
      )}

      {active.length > 0 && (
        <>
          <h2 className="section-label">Active</h2>
          <div className="trade-list">
            {active.map(t => (
              <TradeRow key={t.id} trade={t} onClick={() => navigate(`/trades/${t.id}`)} />
            ))}
          </div>
        </>
      )}

      {history.length > 0 && (
        <>
          <h2 className="section-label" style={{ marginTop: '2rem' }}>History</h2>
          <div className="trade-list">
            {history.map(t => (
              <TradeRow key={t.id} trade={t} onClick={() => navigate(`/trades/${t.id}`)} />
            ))}
          </div>
        </>
      )}

      {showPropose && (
        <div className="modal-overlay" onClick={() => setShowPropose(false)}>
          <div className="modal" style={{ maxWidth: 480 }} onClick={e => e.stopPropagation()}>
            <h2>Propose a Trade</h2>

            <div className="form-group">
              <label>Trade with (username)</label>
              <input
                value={proposeUsername}
                onChange={e => { setProposeUsername(e.target.value); setProposeError('') }}
                placeholder="Enter username"
                autoFocus
              />
            </div>

            <div className="form-group">
              <label>Your Offer</label>
              {proposeItems.length === 0 && (
                <div className="text-muted-sm" style={{ marginBottom: '0.5rem' }}>
                  No cards added yet.
                </div>
              )}
              {proposeItems.map(item => (
                <div key={item.id} className="trade-propose-item">
                  <span>{item.tradeQty}x {item.card.name}</span>
                  <button className="btn btn-ghost btn-sm" onClick={() => removeProposedItem(item.id)}>x</button>
                </div>
              ))}
              <button className="btn btn-ghost btn-sm" style={{ marginTop: '0.25rem' }}
                onClick={() => setShowAddCard(true)}>
                <Plus size={14} /> Add Card
              </button>
            </div>

            {proposeError && <div className="error-msg">{proposeError}</div>}

            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setShowPropose(false)}>Cancel</button>
              <button className="btn btn-primary"
                disabled={!proposeUsername.trim() || proposeItems.length === 0 || propose.isPending}
                onClick={() => propose.mutate()}>
                {propose.isPending ? 'Proposing' : 'Send Proposal'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showAddCard && (
        <TradeAddCardModal
          existingIds={proposeItems.map(i => i.id)}
          onAdd={(entry) => {
            setProposeItems(prev => {
              const exists = prev.find(i => i.id === entry.id)
              if (exists) return prev
              return [...prev, entry]
            })
            setShowAddCard(false)
          }}
          onClose={() => setShowAddCard(false)}
        />
      )}
    </div>
  )
}

function TradeRow({ trade, onClick }) {
  return (
    <div className="trade-row" onClick={onClick}>
      <div className="trade-row-icon">
        <ArrowLeftRight size={16} />
        {trade.is_my_turn && <span className="trade-pending-dot" />}
      </div>
      <div className="trade-row-body">
        <div className="trade-row-title">
          Trade with <strong>{trade.other_username}</strong>
          {trade.is_my_turn && <span className="badge badge-loan" style={{ marginLeft: 8 }}>Your Turn</span>}
        </div>
        <div className="text-muted-sm">
          {trade.updated_at ? new Date(trade.updated_at).toLocaleDateString() : ''}
        </div>
      </div>
      <div>
        <span style={{ color: STATUS_COLOR[trade.status], fontSize: '0.8rem', fontWeight: 600 }}>
          {STATUS_LABEL[trade.status] || trade.status}
        </span>
      </div>
    </div>
  )
}

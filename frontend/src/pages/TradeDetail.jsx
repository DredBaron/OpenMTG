import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate, Navigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, Camera } from 'lucide-react'
import api from '../api'
import { useAuth } from '../hooks/useAuth'
import CONDITION_MULTIPLIERS from '../constants'
import TradeAddCardModal from '../components/TradeAddCardModal'
import CardPhotoViewer from '../components/CardPhotoViewer'
import ConfirmModal from '../components/ConfirmModal'

function tradeTotal(items) {
  return items.reduce((sum, item) => {
    const price = item.card_snapshot_price || 0
    const mult  = CONDITION_MULTIPLIERS[item.condition] ?? 1.0
    return sum + price * mult * item.quantity
  }, 0)
}

function statusMessage(trade, myId) {
  const iAmInitiator = trade.initiator_id === myId
  const other = iAmInitiator ? trade.counterpart_username : trade.initiator_username

  if (trade.status === 'proposed') {
    return iAmInitiator
      ? `Waiting for ${other} to add their cards`
      : `${trade.initiator_username} has proposed a trade, add your cards to respond`
  }
  if (trade.status === 'active') {
    const myConfirmed    = iAmInitiator ? trade.initiator_confirmed : trade.counterpart_confirmed
    const theirConfirmed = iAmInitiator ? trade.counterpart_confirmed : trade.initiator_confirmed
    if (myConfirmed && theirConfirmed) return 'Both parties confirmed. Processing.'
    if (myConfirmed)   return `Waiting for ${other} to confirm`
    if (theirConfirmed) return `${other} has confirmed. Review and confirm to complete`
    return `Trade in progress. Review ${other}'s offer and confirm when ready`
  }
  if (trade.status === 'accepted')  return 'Trade accepted. Cards have been transferred'
  if (trade.status === 'rejected')  return 'Trade rejected.'
  if (trade.status === 'cancelled') return 'Trade cancelled.'
  return ''
}

export default function TradeDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { user, tradesEnabled } = useAuth()
  const [showAddCard, setShowAddCard] = useState(false)
  const [pendingItems, setPendingItems] = useState(null)
  const [viewPhotos, setViewPhotos] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null)

  const { data: trade, isLoading } = useQuery({
    queryKey: ['trade', id],
    queryFn: () => api.get(`/trades/${id}`).then(r => r.data),
    refetchInterval: 15000,
  })

  const seededItems = useMemo(() => (trade?.my_items ?? []).map(i => ({
    id: i.collection_entry_id,
    tradeQty: i.quantity,
    card: {
      name: i.card_snapshot_name,
      image_uri: i.card_snapshot_image,
      price_usd:      i.foil ? null : i.card_snapshot_price,
      price_usd_foil: i.foil ? i.card_snapshot_price : null,
    },
    condition: i.condition,
    foil: i.foil,
    quantity: 999,
  })), [trade])

  useEffect(() => {
    if (trade) document.title = `Trade with ${
      trade.initiator_id === user?.id ? trade.counterpart_username : trade.initiator_username
    } - OpenMTG`
  }, [trade, user])

  const updateItems = useMutation({
    mutationFn: (items) => api.put(`/trades/${id}/items`, {
      items: items.map(i => ({ collection_entry_id: i.id, quantity: i.tradeQty })),
    }),
    onSuccess: () => {
      qc.invalidateQueries(['trade', id])
      qc.invalidateQueries(['trades'])
      qc.invalidateQueries(['trades-pending'])
      setPendingItems(null)
    },
  })

  const confirm = useMutation({
    mutationFn: () => api.post(`/trades/${id}/confirm`),
    onSuccess: () => {
      qc.invalidateQueries(['trade', id])
      qc.invalidateQueries(['trades'])
      qc.invalidateQueries(['trades-pending'])
    },
  })

  const unconfirm = useMutation({
    mutationFn: () => api.post(`/trades/${id}/unconfirm`),
    onSuccess: () => {
      qc.invalidateQueries(['trade', id])
      qc.invalidateQueries(['trades'])
      qc.invalidateQueries(['trades-pending'])
    },
  })

  const reject = useMutation({
    mutationFn: () => api.post(`/trades/${id}/reject`),
    onSuccess: () => {
      qc.invalidateQueries(['trades'])
      qc.invalidateQueries(['trades-pending'])
      navigate('/trades')
    },
  })

  if (!tradesEnabled) return <Navigate to="/collection" replace />
  if (isLoading) return <div className="loading">Loading trade</div>
  if (!trade)    return <div className="empty-state"><p>Trade not found.</p></div>

  const myId        = user?.id
  const isOpen      = ['proposed', 'active'].includes(trade.status)
  const iAmInitiator = trade.initiator_id === myId
  const myConfirmed  = iAmInitiator ? trade.initiator_confirmed : trade.counterpart_confirmed
  const otherName    = iAmInitiator ? trade.counterpart_username : trade.initiator_username

  const displayMyItems = pendingItems ?? seededItems

  const myTotal = displayMyItems.reduce((sum, i) => {
    const price = (i.foil && i.card?.price_usd_foil)
      ? i.card.price_usd_foil
      : (i.card?.price_usd ?? 0)
    const mult = CONDITION_MULTIPLIERS[i.condition] ?? 1.0
    return sum + price * mult * i.tradeQty
  }, 0)
  const theirTotal = tradeTotal(trade.their_items)

  const pendingChanged = pendingItems !== null && JSON.stringify(
    pendingItems.map(i => ({ id: i.id, qty: i.tradeQty }))
  ) !== JSON.stringify(
    trade.my_items.map(i => ({ id: i.collection_entry_id, qty: i.quantity }))
  )

  const removeItem = (entryId) =>
    setPendingItems(prev => (prev ?? seededItems).filter(i => i.id !== entryId))

  const existingIds = displayMyItems.map(i => i.id)

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Trade with {otherName}</h1>
          <div className="page-subtitle trade-status-msg">
            {statusMessage(trade, myId)}
          </div>
        </div>
        <div className="flex-gap">
          {isOpen && (
            <button className="btn btn-danger btn-sm"
              onClick={() => setConfirmAction({
                message: iAmInitiator && trade.status === 'proposed'
                  ? 'Cancel this trade proposal?'
                  : 'Reject this trade?',
                onConfirm: () => { reject.mutate(); setConfirmAction(null) },
              })}>
              {iAmInitiator && trade.status === 'proposed' ? 'Cancel' : 'Reject'}
            </button>
          )}
        </div>
      </div>

      <div className="trade-split">
        {/* My side */}
        <div className="trade-side">
          <div className="trade-side-header">Your Offer</div>
          <div className="trade-items-list">
            {displayMyItems.length === 0 && (
              <div className="text-muted-sm" style={{ padding: '0.5rem 0' }}>No cards added yet.</div>
            )}
            {displayMyItems.map(item => (
              <div key={item.id} className="trade-item-row">
                {item.card.image_uri && (
                  <img src={item.card.image_uri} alt={item.card.name} className="trade-item-thumb" />
                )}
                <div className="trade-item-info">
                  <div className="trade-item-name">{item.card.name}</div>
                  <div className="text-muted-xs">
                    {item.condition}{item.foil ? ' | Foil' : ''} | x{item.tradeQty}
                  </div>
                </div>
                {isOpen && pendingItems !== null && (
                  <button className="btn btn-ghost btn-sm" onClick={() => removeItem(item.id)}>
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            ))}
          </div>

          {isOpen && (
            <button className="btn btn-ghost btn-sm trade-add-btn"
              onClick={() => setShowAddCard(true)}>
              <Plus size={14} /> Add Card
            </button>
          )}

          <div className="trade-total">
            <span>Total</span>
            <span className="trade-total-value">
              ${myTotal.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Their side */}
        <div className="trade-side trade-side-readonly">
          <div className="trade-side-header">{otherName}'s Offer</div>
          <div className="trade-items-list">
            {trade.their_items.length === 0 && (
              <div className="text-muted-sm" style={{ padding: '0.5rem 0' }}>
                {trade.status === 'proposed' ? 'Waiting for their response...' : 'No cards offered.'}
              </div>
            )}
            {trade.their_items.map(item => (
              <div key={item.id} className="trade-item-row">
                {item.card_snapshot_image && (
                  <img src={item.card_snapshot_image} alt={item.card_snapshot_name} className="trade-item-thumb" />
                )}
                <div className="trade-item-info">
                  <div className="trade-item-name">{item.card_snapshot_name}</div>
                  <div className="text-muted-xs">
                    {item.condition}{item.foil ? ' | Foil' : ''} | x{item.quantity}
                  </div>
                </div>
                <button className="btn btn-ghost btn-sm"
                  title="View photos"
                  onClick={() => setViewPhotos({ entryId: item.collection_entry_id, name: item.card_snapshot_name })}>
                  <Camera size={13} />
                </button>
              </div>
            ))}
          </div>

          <div className="trade-total">
            <span>Total</span>
            <span className="trade-total-value">${theirTotal.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Action bar */}
      {isOpen && (
        <div className="trade-action-bar">
          {pendingChanged && (
            <button className="btn btn-ghost"
              onClick={() => updateItems.mutate(pendingItems)}
              disabled={updateItems.isPending}>
              {updateItems.isPending ? 'Saving' : 'Save Changes'}
            </button>
          )}
          {!pendingChanged && trade.status === 'active' && !myConfirmed && (
            <button className="btn btn-primary"
              disabled={confirm.isPending || trade.my_items.length === 0 || trade.their_items.length === 0}
              onClick={() => confirm.mutate()}>
              {confirm.isPending ? 'Confirming…' : 'Confirm Trade'}
            </button>
          )}
          {!pendingChanged && trade.status === 'active' && myConfirmed && (
            <button className="btn btn-ghost"
              disabled={unconfirm.isPending}
              onClick={() => unconfirm.mutate()}>
              {unconfirm.isPending ? 'Retracting…' : 'Un-submit'}
            </button>
          )}
          {trade.status === 'proposed' && !iAmInitiator && (
            <button className="btn btn-primary"
              disabled={displayMyItems.length === 0 || updateItems.isPending}
              onClick={() => updateItems.mutate(displayMyItems)}>
              {updateItems.isPending ? 'Sending' : 'Send Response'}
            </button>
          )}
        </div>
      )}

      {showAddCard && (
        <TradeAddCardModal
          existingIds={existingIds}
          onAdd={(entry) => {
            setPendingItems(prev => [...(prev ?? seededItems), entry])
            setShowAddCard(false)
          }}
          onClose={() => setShowAddCard(false)}
        />
      )}

      {viewPhotos && (
        <CardPhotoViewer
          entryId={viewPhotos.entryId}
          cardName={viewPhotos.name}
          photos={[{ side: 'front' }, { side: 'back' }]}
          tradeId={parseInt(id)}
          onClose={() => setViewPhotos(null)}
        />
      )}

      {confirmAction && (
        <ConfirmModal
          message={confirmAction.message}
          onConfirm={confirmAction.onConfirm}
          onCancel={() => setConfirmAction(null)}
        />
      )}
    </div>
  )
}

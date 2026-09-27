import logging
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from database_trades import get_trades_db
from features import is_enabled, require_feature
from security import get_current_user
import services.webhooks as webhooks

import models
import schemas
from models.trade import Trade, TradeItem

# /status stays reachable while the feature is off; main.py registers it before `router`, whose
# GET /{trade_id} would otherwise capture it. Authentication runs before the feature check so an
# anonymous caller still gets 401.
status_router = APIRouter(prefix="/trades", tags=["trades"])
router = APIRouter(
    prefix="/trades",
    tags=["trades"],
    dependencies=[Depends(get_current_user), Depends(require_feature("trades_enabled"))],
)

logger = logging.getLogger(__name__)

# Lifecycle: proposed -> active (pending; both parties can confirm) -> processing (cards are
# being transferred) -> accepted (completed). rejected and cancelled close an open trade.
OPEN_STATUSES = ("proposed", "active")
PROCESSING = "processing"


def _conflict(detail: str = "This trade changed while your request was being handled. "
                            "Reload it and try again.") -> HTTPException:
    return HTTPException(status_code=409, detail=detail)


def _reject_if_processing(trade: "Trade") -> None:
    if trade.status == PROCESSING:
        raise _conflict("This trade is being processed. Reload it in a moment.")


@status_router.get("/status")
def trades_status(db_main: Session = Depends(get_db)):
    return {"enabled": is_enabled(db_main, "trades_enabled")}

UPLOADS_PATH = os.environ.get("UPLOADS_PATH", "/data/uploads")


def _require_participant(trade: Trade, user_id: int):
    if user_id not in (trade.initiator_id, trade.counterpart_id):
        raise HTTPException(status_code=403, detail="Not a participant in this trade")


def _get_trade(trade_id: int, db_trades: Session) -> Trade:
    trade = db_trades.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


def _snapshot(entry) -> dict:
    card = entry.card
    price = card.price_usd_foil if entry.foil and card.price_usd_foil else card.price_usd
    return {
        "card_snapshot_name":  card.name,
        "card_snapshot_image": card.image_uri,
        "card_snapshot_price": price,
        "foil":                entry.foil,
        "condition":           entry.condition,
    }


def _resolve_users(trade: Trade, db_main: Session):
    initiator   = db_main.query(models.User).filter_by(id=trade.initiator_id).first()
    counterpart = db_main.query(models.User).filter_by(id=trade.counterpart_id).first()
    return initiator, counterpart


def _build_trade_out(trade: Trade, current_user_id: int, db_main: Session) -> schemas.TradeOut:
    initiator, counterpart = _resolve_users(trade, db_main)
    my_items    = [i for i in trade.items if i.user_id == current_user_id]
    their_items = [i for i in trade.items if i.user_id != current_user_id]
    return schemas.TradeOut(
        id=trade.id,
        initiator_id=trade.initiator_id,
        counterpart_id=trade.counterpart_id,
        status=trade.status,
        initiator_confirmed=trade.initiator_confirmed,
        counterpart_confirmed=trade.counterpart_confirmed,
        last_actor_id=trade.last_actor_id,
        my_items=[schemas.TradeItemOut.model_validate(i) for i in my_items],
        their_items=[schemas.TradeItemOut.model_validate(i) for i in their_items],
        initiator_username=initiator.username if initiator else "unknown",
        counterpart_username=counterpart.username if counterpart else "unknown",
        created_at=trade.created_at,
        updated_at=trade.updated_at,
    )


@router.get("/pending-count")
def pending_count(
    db_trades: Session = Depends(get_trades_db),
    current_user: models.User = Depends(get_current_user),
):
    uid = current_user.id
    count = db_trades.query(func.count(Trade.id)).filter(
        ((Trade.initiator_id == uid) | (Trade.counterpart_id == uid)),
        Trade.status.in_(["proposed", "active"]),
        Trade.last_actor_id != uid,
    ).scalar() or 0
    return {"count": count}


@router.get("", response_model=list[schemas.TradeListItemOut])
def list_trades(
    db_trades: Session = Depends(get_trades_db),
    db_main: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    uid = current_user.id
    trades = (
        db_trades.query(Trade)
        .filter((Trade.initiator_id == uid) | (Trade.counterpart_id == uid))
        .order_by(Trade.updated_at.desc())
        .limit(50)
        .all()
    )

    user_ids = set()
    for t in trades:
        user_ids.add(t.initiator_id)
        user_ids.add(t.counterpart_id)
    users = {u.id: u.username for u in db_main.query(models.User).filter(models.User.id.in_(user_ids)).all()}

    result = []
    for t in trades:
        other_id = t.counterpart_id if t.initiator_id == uid else t.initiator_id
        is_my_turn = t.last_actor_id != uid and t.status in ("proposed", "active")
        result.append(schemas.TradeListItemOut(
            id=t.id,
            status=t.status,
            other_username=users.get(other_id, "unknown"),
            initiator_confirmed=t.initiator_confirmed,
            counterpart_confirmed=t.counterpart_confirmed,
            is_my_turn=is_my_turn,
            updated_at=t.updated_at,
        ))
    return result


@router.post("", response_model=schemas.TradeOut, status_code=201)
def propose_trade(
    payload: schemas.ProposeTradeRequest,
    db_trades: Session = Depends(get_trades_db),
    db_main: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    counterpart = db_main.query(models.User).filter(
        func.lower(models.User.username) == payload.counterpart_username.lower()
    ).first()
    if not counterpart:
        raise HTTPException(status_code=404, detail="User not found")
    if counterpart.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot trade with yourself")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Must include at least one card")

    trade = Trade(
        initiator_id=current_user.id,
        counterpart_id=counterpart.id,
        status="proposed",
        last_actor_id=current_user.id,
    )
    db_trades.add(trade)
    db_trades.flush()

    for item_in in payload.items:
        entry = (
            db_main.query(models.CollectionEntry)
            .options(joinedload(models.CollectionEntry.card))
            .filter_by(id=item_in.collection_entry_id, user_id=current_user.id)
            .first()
        )
        if not entry:
            db_trades.rollback()
            raise HTTPException(status_code=404, detail=f"Collection entry {item_in.collection_entry_id} not found")
        if entry.quantity < item_in.quantity:
            db_trades.rollback()
            raise HTTPException(status_code=400,
                detail=f"Not enough copies of {entry.card.name} (have {entry.quantity}, offering {item_in.quantity})")

        snap = _snapshot(entry)
        db_trades.add(TradeItem(
            trade_id=trade.id,
            user_id=current_user.id,
            collection_entry_id=item_in.collection_entry_id,
            quantity=item_in.quantity,
            **snap,
        ))

    db_trades.commit()
    db_trades.refresh(trade)
    webhooks.notify_trade_event(db_main, trade, "proposed", current_user, counterpart)
    return _build_trade_out(trade, current_user.id, db_main)


@router.get("/{trade_id}", response_model=schemas.TradeOut)
def get_trade(
    trade_id: int,
    db_trades: Session = Depends(get_trades_db),
    db_main: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    trade = _get_trade(trade_id, db_trades)
    _require_participant(trade, current_user.id)
    return _build_trade_out(trade, current_user.id, db_main)


@router.put("/{trade_id}/items", response_model=schemas.TradeOut)
def update_items(
    trade_id: int,
    payload: schemas.UpdateTradeItemsRequest,
    db_trades: Session = Depends(get_trades_db),
    db_main: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    trade = _get_trade(trade_id, db_trades)
    _require_participant(trade, current_user.id)
    _reject_if_processing(trade)

    if trade.status not in OPEN_STATUSES:
        raise HTTPException(status_code=400, detail="Trade is not open for modification")

    if not payload.items:
        raise HTTPException(status_code=400, detail="Must include at least one card")

    became_active = trade.status == "proposed" and current_user.id == trade.counterpart_id

    # Reset both confirmations in the same transaction as the item rewrite, and only
    # while the trade is still open. A concurrent confirm can then never claim the
    # trade with items the other party has not seen.
    changes = {
        Trade.initiator_confirmed:   False,
        Trade.counterpart_confirmed: False,
        Trade.last_actor_id:         current_user.id,
    }
    if became_active:
        changes[Trade.status] = "active"
    if not _update_if_status(db_trades, trade.id, OPEN_STATUSES, changes):
        db_trades.rollback()
        raise _conflict()

    db_trades.query(TradeItem).filter_by(trade_id=trade.id, user_id=current_user.id).delete()
    db_trades.flush()

    for item_in in payload.items:
        entry = (
            db_main.query(models.CollectionEntry)
            .options(joinedload(models.CollectionEntry.card))
            .filter_by(id=item_in.collection_entry_id, user_id=current_user.id)
            .first()
        )
        if not entry:
            db_trades.rollback()
            raise HTTPException(status_code=404, detail=f"Collection entry {item_in.collection_entry_id} not found")
        if entry.quantity < item_in.quantity:
            db_trades.rollback()
            raise HTTPException(status_code=400,
                detail=f"Not enough copies of {entry.card.name} (have {entry.quantity}, offering {item_in.quantity})")

        snap = _snapshot(entry)
        db_trades.add(TradeItem(
            trade_id=trade.id,
            user_id=current_user.id,
            collection_entry_id=item_in.collection_entry_id,
            quantity=item_in.quantity,
            **snap,
        ))

    db_trades.commit()
    db_trades.refresh(trade)

    initiator, counterpart = _resolve_users(trade, db_main)
    webhooks.notify_trade_event(db_main, trade, "updated", initiator, counterpart)
    if became_active:
        webhooks.notify_trade_event(db_main, trade, "engaged", initiator, counterpart)

    return _build_trade_out(trade, current_user.id, db_main)


@router.post("/{trade_id}/confirm", response_model=schemas.TradeOut)
def confirm_trade(
    trade_id: int,
    db_trades: Session = Depends(get_trades_db),
    db_main: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    trade = _get_trade(trade_id, db_trades)
    _require_participant(trade, current_user.id)
    _reject_if_processing(trade)

    if trade.status != "active":
        raise HTTPException(status_code=400, detail="Trade must be active before confirming")

    my_items = db_trades.query(TradeItem).filter_by(trade_id=trade.id, user_id=current_user.id).all()
    if not my_items:
        raise HTTPException(status_code=400, detail="You must add cards to the trade before confirming")

    my_flag = _confirm_flag(trade, current_user.id)
    if not _update_if_status(db_trades, trade.id, ("active",),
                             {my_flag: True, Trade.last_actor_id: current_user.id}):
        db_trades.rollback()
        raise _conflict()
    db_trades.commit()
    db_trades.refresh(trade)

    if trade.initiator_confirmed and trade.counterpart_confirmed:
        _complete_trade(trade, my_flag, db_trades, db_main)

    db_trades.refresh(trade)
    return _build_trade_out(trade, current_user.id, db_main)


@router.post("/{trade_id}/unconfirm", response_model=schemas.TradeOut)
def unconfirm_trade(
    trade_id: int,
    db_trades: Session = Depends(get_trades_db),
    db_main: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    trade = _get_trade(trade_id, db_trades)
    _require_participant(trade, current_user.id)
    _reject_if_processing(trade)

    if trade.status != "active":
        raise HTTPException(status_code=400, detail="Trade must be active to un-submit")

    my_confirmed = (trade.initiator_confirmed if current_user.id == trade.initiator_id
                    else trade.counterpart_confirmed)
    if not my_confirmed:
        raise HTTPException(status_code=400, detail="You have not confirmed this trade")

    my_flag = _confirm_flag(trade, current_user.id)
    if not _update_if_status(db_trades, trade.id, ("active",),
                             {my_flag: False, Trade.last_actor_id: current_user.id}):
        db_trades.rollback()
        raise _conflict()
    db_trades.commit()
    db_trades.refresh(trade)
    return _build_trade_out(trade, current_user.id, db_main)


def _confirm_flag(trade: Trade, user_id: int):
    return Trade.initiator_confirmed if user_id == trade.initiator_id else Trade.counterpart_confirmed


def _update_if_status(db_trades: Session, trade_id: int, statuses: tuple, changes: dict) -> bool:
    """UPDATE trades SET <changes> WHERE id = ? AND status IN (<statuses>).

    Returns True if the row changed. Every state change goes through this so a request
    working from a stale read can never act on a trade that has since moved on.
    """
    updated = (
        db_trades.query(Trade)
        .filter(Trade.id == trade_id, Trade.status.in_(statuses))
        .update(changes, synchronize_session=False)
    )
    return updated == 1


def _claim_for_processing(db_trades: Session, trade_id: int) -> bool:
    """Atomically move a fully confirmed, pending trade to processing.

    UPDATE trades SET status = 'processing'
    WHERE id = ? AND status = 'active' AND initiator_confirmed AND counterpart_confirmed

    Only the request whose UPDATE changes the row may run the transfer. Any other request
    (a double click, or both parties confirming at the same moment) changes no rows.
    """
    claimed = (
        db_trades.query(Trade)
        .filter(
            Trade.id == trade_id,
            Trade.status == "active",
            Trade.initiator_confirmed == True,   # noqa: E712
            Trade.counterpart_confirmed == True,  # noqa: E712
        )
        .update({Trade.status: PROCESSING}, synchronize_session=False)
    )
    db_trades.commit()
    return claimed == 1


def _complete_trade(trade: Trade, my_flag, db_trades: Session, db_main: Session) -> None:
    """pending -> processing -> completed, or back to pending if the transfer fails."""
    if not _claim_for_processing(db_trades, trade.id):
        raise _conflict("This trade is already being processed or has changed. Reload it.")

    try:
        _execute_transfer(trade, db_trades, db_main)
    except AlreadyTransferred:
        # The cards moved in an earlier attempt (the marker commits with the card moves), so
        # the trade is complete. Nothing was changed by this attempt.
        db_main.rollback()
        logger.error("Trade %s: refused a second transfer; marking it completed", trade.id)
        _mark_completed(db_trades, trade.id)
        raise _conflict("This trade has already been completed. Reload it.")
    except Exception:
        # Undo any card changes in the main database FIRST, then return the trade to
        # pending with this party's confirmation cleared so they can review and retry.
        db_main.rollback()
        _release_processing(db_trades, trade.id, my_flag)
        raise

    try:
        _mark_completed(db_trades, trade.id, raise_errors=True)
    except Exception:
        logger.critical("Trade %s: cards were transferred but the trade could not be marked "
                        "completed. It will be completed at the next startup.", trade.id)
        raise

    db_trades.refresh(trade)
    initiator, counterpart = _resolve_users(trade, db_main)
    webhooks.notify_trade_event(db_main, trade, "accepted", initiator, counterpart)


class AlreadyTransferred(Exception):
    """The trade's cards have already been moved (its transfer marker exists)."""


def _record_transfer(db_main: Session, trade_id: int) -> None:
    """Write the trade's transfer marker into the open main-database transaction.

    It commits together with the card moves, so it exists exactly when the cards moved. The unique
    trade_id rejects a second transfer of the same trade before any card is touched."""
    db_main.add(models.TradeTransfer(trade_id=trade_id))
    try:
        db_main.flush()
    except IntegrityError:
        raise AlreadyTransferred(trade_id)


def _mark_completed(db_trades: Session, trade_id: int, raise_errors: bool = False) -> None:
    """processing -> accepted (completed)."""
    try:
        _update_if_status(db_trades, trade_id, (PROCESSING,), {Trade.status: "accepted"})
        db_trades.commit()
    except Exception:
        db_trades.rollback()
        if raise_errors:
            raise
        logger.exception("Trade %s could not be marked completed; it will be completed at the "
                         "next startup", trade_id)


def _release_processing(db_trades: Session, trade_id: int, my_flag) -> None:
    try:
        db_trades.rollback()
        _update_if_status(db_trades, trade_id, (PROCESSING,),
                          {Trade.status: "active", my_flag: False})
        db_trades.commit()
    except Exception:
        db_trades.rollback()
        logger.exception("Trade %s could not be returned to pending; it will be reset at "
                         "the next startup", trade_id)


def _execute_transfer(trade: Trade, db_trades: Session, db_main: Session):
    # First, so an already-transferred trade is recognised before any check or card change.
    _record_transfer(db_main, trade.id)

    all_items = db_trades.query(TradeItem).filter_by(trade_id=trade.id).all()

    for item in all_items:
        # Items saved before quantities were validated at the API could hold 0 or a
        # negative number, which would move cards in the wrong direction.
        if item.quantity is None or item.quantity < 1:
            raise HTTPException(status_code=400,
                detail=f"Trade item {item.card_snapshot_name!r} has an invalid quantity; "
                       "update the trade items before confirming")
        src_entry = (
            db_main.query(models.CollectionEntry)
            .options(joinedload(models.CollectionEntry.card))
            .filter_by(id=item.collection_entry_id, user_id=item.user_id)
            .first()
        )
        if not src_entry:
            raise HTTPException(status_code=400,
                detail=f"Card {item.card_snapshot_name!r} is no longer in the collection")
        if src_entry.quantity < item.quantity:
            raise HTTPException(status_code=400,
                detail=f"Not enough copies of {item.card_snapshot_name!r} to complete the trade")

    for item in all_items:
        dst_user_id = trade.counterpart_id if item.user_id == trade.initiator_id else trade.initiator_id

        src_entry = (
            db_main.query(models.CollectionEntry)
            .options(joinedload(models.CollectionEntry.card))
            .filter_by(id=item.collection_entry_id, user_id=item.user_id)
            .first()
        )

        src_entry.quantity -= item.quantity
        if src_entry.quantity <= 0:
            db_main.delete(src_entry)
        else:
            db_main.flush()

        existing_dst = (
            db_main.query(models.CollectionEntry)
            .filter_by(
                user_id=dst_user_id,
                card_id=src_entry.card_id,
                foil=src_entry.foil,
                condition=src_entry.condition,
                language=src_entry.language,
            )
            .first()
        )
        if existing_dst:
            existing_dst.quantity += item.quantity
        else:
            db_main.add(models.CollectionEntry(
                user_id=dst_user_id,
                card_id=src_entry.card_id,
                quantity=item.quantity,
                foil=src_entry.foil,
                condition=src_entry.condition,
                language=src_entry.language,
            ))

    db_main.commit()


@router.post("/{trade_id}/reject", response_model=schemas.TradeOut)
def reject_trade(
    trade_id: int,
    db_trades: Session = Depends(get_trades_db),
    db_main: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    trade = _get_trade(trade_id, db_trades)
    _require_participant(trade, current_user.id)
    _reject_if_processing(trade)

    if trade.status not in OPEN_STATUSES:
        raise HTTPException(status_code=400, detail="Trade is already closed")

    new_status = ("cancelled" if trade.status == "proposed" and current_user.id == trade.initiator_id
                  else "rejected")
    if not _update_if_status(db_trades, trade.id, OPEN_STATUSES,
                             {Trade.status: new_status, Trade.last_actor_id: current_user.id}):
        db_trades.rollback()
        raise _conflict()
    db_trades.commit()
    db_trades.refresh(trade)

    initiator, counterpart = _resolve_users(trade, db_main)
    webhooks.notify_trade_event(db_main, trade, trade.status, initiator, counterpart)

    return _build_trade_out(trade, current_user.id, db_main)


@router.get("/{trade_id}/photos/{entry_id}/{side}")
def trade_photo(
    trade_id: int,
    entry_id: int,
    side: str,
    db_trades: Session = Depends(get_trades_db),
    db_main: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if side not in ("front", "back"):
        raise HTTPException(status_code=400, detail="Side must be 'front' or 'back'")

    trade = _get_trade(trade_id, db_trades)
    _require_participant(trade, current_user.id)

    item = db_trades.query(TradeItem).filter_by(trade_id=trade.id, collection_entry_id=entry_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Entry not part of this trade")

    photo = db_main.query(models.CardPhoto).filter_by(
        collection_entry_id=entry_id, side=side
    ).first()
    if not photo or not os.path.exists(photo.file_path):
        raise HTTPException(status_code=404, detail="Photo not found")

    return FileResponse(photo.file_path)

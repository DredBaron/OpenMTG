from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone

import models
import services.scryfall as scryfall_service
from database import get_db
from routers.auth import get_current_user

router = APIRouter(prefix="/wishlist", tags=["wishlist"])

class WishlistEntryCreate(BaseModel):
    scryfall_id:  str
    target_price: Optional[float] = None
    foil:         bool            = False
    notes:        Optional[str]   = None


class WishlistEntryUpdate(BaseModel):
    scryfall_id:  Optional[str]   = None
    foil:         Optional[bool]  = None
    target_price: Optional[float] = None
    notes:        Optional[str]   = None

def _serialize(entry: models.WishlistEntry, currency: str = "usd") -> dict:
    card = entry.card
    foil = entry.foil

    if currency == "eur":
        current = card.price_eur_foil if foil else card.price_eur
    else:
        current = card.price_usd_foil if foil else card.price_usd

    price_met = (
        entry.target_price is not None
        and current is not None
        and current <= entry.target_price
    )

    return {
        "id":               entry.id,
        "scryfall_id":      card.scryfall_id,
        "name":             card.name,
        "set_name":         card.set_name or "",
        "set_code":         card.set_code or "",
        "collector_number": card.collector_number or "",
        "image_uri":        card.image_uri,
        "rarity":           card.rarity,
        "price_usd":        card.price_usd,
        "price_usd_foil":   card.price_usd_foil,
        "price_eur":        card.price_eur,
        "price_eur_foil":   card.price_eur_foil,
        "target_price":     entry.target_price,
        "foil":             entry.foil,
        "notes":            entry.notes,
        "added_at":         entry.added_at.isoformat() if entry.added_at else "",
        "price_met":        price_met,
    }

@router.get("")
def list_wishlist(
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entries = (
        db.query(models.WishlistEntry)
        .filter(models.WishlistEntry.user_id == current_user.id)
        .order_by(models.WishlistEntry.added_at.desc())
        .all()
    )
    currency = current_user.preferred_currency or "usd"
    return [_serialize(e, currency) for e in entries]


@router.post("", status_code=status.HTTP_201_CREATED)
def add_to_wishlist(
    body:         WishlistEntryCreate,
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    card = scryfall_service.get_card_by_scryfall_id(body.scryfall_id, db)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found on Scryfall")

    existing = (
        db.query(models.WishlistEntry)
        .filter_by(user_id=current_user.id, card_id=card.id, foil=body.foil)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Card already on wishlist")

    entry = models.WishlistEntry(
        user_id=current_user.id,
        card_id=card.id,
        target_price=body.target_price,
        foil=body.foil,
        notes=body.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    currency = current_user.preferred_currency or "usd"
    return _serialize(entry, currency)


@router.patch("/{entry_id}")
def update_wishlist_entry(
    entry_id:     int,
    body:         WishlistEntryUpdate,
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entry = (
        db.query(models.WishlistEntry)
        .filter_by(id=entry_id, user_id=current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Wishlist entry not found")

    new_card_id = entry.card_id
    if body.scryfall_id is not None:
        card = scryfall_service.get_card_by_scryfall_id(body.scryfall_id, db)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found on Scryfall")
        new_card_id = card.id

    new_foil = body.foil if body.foil is not None else entry.foil

    if new_card_id != entry.card_id or new_foil != entry.foil:
        conflict = (
            db.query(models.WishlistEntry)
            .filter_by(user_id=current_user.id, card_id=new_card_id, foil=new_foil)
            .filter(models.WishlistEntry.id != entry_id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=409, detail="That card is already on your wishlist")

    entry.card_id      = new_card_id
    entry.foil         = new_foil
    entry.target_price = body.target_price
    if body.notes is not None:
        entry.notes = body.notes

    db.commit()
    db.refresh(entry)

    currency = current_user.preferred_currency or "usd"
    return _serialize(entry, currency)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_wishlist(
    entry_id:     int,
    db:           Session     = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entry = (
        db.query(models.WishlistEntry)
        .filter_by(id=entry_id, user_id=current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Wishlist entry not found")

    db.delete(entry)
    db.commit()


@router.get("/{entry_id}/history")
def get_price_history(
    entry_id: int,
    days:     int         = 90,
    db:       Session     = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entry = (
        db.query(models.WishlistEntry)
        .filter_by(id=entry_id, user_id=current_user.id)
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Wishlist entry not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    history = (
        db.query(models.PriceHistory)
        .filter(
            models.PriceHistory.card_id == entry.card_id,
            models.PriceHistory.recorded_at >= cutoff,
        )
        .order_by(models.PriceHistory.recorded_at.asc())
        .all()
    )

    return [
        {
            "recorded_at":    h.recorded_at.isoformat(),
            "price_usd":      h.price_usd,
            "price_usd_foil": h.price_usd_foil,
            "price_eur":      h.price_eur,
            "price_eur_foil": h.price_eur_foil,
        }
        for h in history
    ]
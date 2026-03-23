from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from database import get_db
from security import get_current_user
from pydantic import BaseModel

import httpx
import models.models as models
import schemas
import services.scryfall as scryfall_service

router = APIRouter(prefix="/collection", tags=["collection"])


class AddCardRequest(BaseModel):
    scryfall_id: str
    quantity: int = 1
    foil: bool = False
    condition: str = "NM"
    language: str = "en"
    notes: str | None = None


class UpdateCardRequest(BaseModel):
    quantity: int | None = None
    foil: bool | None = None
    condition: str | None = None
    language: str | None = None
    notes: str | None = None
    scryfall_id: str | None = None


@router.get("", response_model=list[schemas.CollectionEntryOut])
def get_collection(
    search: str | None = Query(None, description="Filter by card name"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = (
        db.query(models.CollectionEntry)
        .options(joinedload(models.CollectionEntry.card))
        .filter(models.CollectionEntry.user_id == current_user.id)
    )
    if search:
        query = query.join(models.Card).filter(
            models.Card.name.ilike(f"%{search}%")
        )
    return query.order_by(models.CollectionEntry.added_at.desc()).all()


@router.post("", response_model=schemas.CollectionEntryOut, status_code=201)
def add_card(
    payload: AddCardRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    card = scryfall_service.get_card_by_scryfall_id(payload.scryfall_id, db)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found on Scryfall")

    existing = (
        db.query(models.CollectionEntry)
        .filter(
            models.CollectionEntry.user_id == current_user.id,
            models.CollectionEntry.card_id == card.id,
            models.CollectionEntry.foil == payload.foil,
            models.CollectionEntry.condition == payload.condition,
            models.CollectionEntry.language == payload.language,
        )
        .first()
    )

    if existing:
        existing.quantity += payload.quantity
        db.commit()
        db.refresh(existing)
        return existing

    entry = models.CollectionEntry(
        user_id=current_user.id,
        card_id=card.id,
        quantity=payload.quantity,
        foil=payload.foil,
        condition=payload.condition,
        language=payload.language,
        notes=payload.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=schemas.CollectionEntryOut)
def update_entry(
    entry_id: int,
    payload: UpdateCardRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entry = (
        db.query(models.CollectionEntry)
        .options(joinedload(models.CollectionEntry.card))
        .filter(
            models.CollectionEntry.id == entry_id,
            models.CollectionEntry.user_id == current_user.id,
        )
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Collection entry not found")

    if payload.scryfall_id and payload.scryfall_id != entry.card.scryfall_id:
        card = scryfall_service.get_card_by_scryfall_id(payload.scryfall_id, db)
        if not card:
            raise HTTPException(status_code=404, detail="Replacement card not found on Scryfall")
        entry.card_id = card.id

    if payload.quantity is not None:
        entry.quantity = payload.quantity
    if payload.foil is not None:
        entry.foil = payload.foil
    if payload.condition is not None:
        entry.condition = payload.condition
    if payload.language is not None:
        entry.language = payload.language
    if payload.notes is not None:
        entry.notes = payload.notes

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def remove_card(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entry = (
        db.query(models.CollectionEntry)
        .filter(
            models.CollectionEntry.id == entry_id,
            models.CollectionEntry.user_id == current_user.id,
        )
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Collection entry not found")

    db.delete(entry)
    db.commit()

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entries = (
        db.query(models.CollectionEntry)
        .options(joinedload(models.CollectionEntry.card))
        .filter(models.CollectionEntry.user_id == current_user.id)
        .all()
    )

    if not entries:
        return {}

    total_cards = sum(e.quantity for e in entries)
    unique_cards = len(entries)

    # Value
    def entry_value(e):
        price = e.card.price_usd_foil if e.foil and e.card.price_usd_foil else e.card.price_usd
        return (price or 0) * e.quantity

    total_value = sum(entry_value(e) for e in entries)

    # Sets
    sets = set(e.card.set_code for e in entries)

    # Rarity
    rarity_count = {}
    rarity_value = {}
    for e in entries:
        r = e.card.rarity or "unknown"
        rarity_count[r] = rarity_count.get(r, 0) + e.quantity
        rarity_value[r] = rarity_value.get(r, 0) + entry_value(e)

    # Colors
    color_count = {}
    for e in entries:
        colors = e.card.color_identity or ""
        if not colors:
            color_count["Colorless"] = color_count.get("Colorless", 0) + e.quantity
        else:
            for c in colors:
                name = {"W":"White","U":"Blue","B":"Black","R":"Red","G":"Green"}.get(c, c)
                color_count[name] = color_count.get(name, 0) + e.quantity

    # Card types
    type_count = {}
    type_keywords = ["Creature","Instant","Sorcery","Enchantment","Artifact","Planeswalker","Land","Battle"]
    for e in entries:
        tl = e.card.type_line or ""
        matched = False
        for t in type_keywords:
            if t in tl:
                type_count[t] = type_count.get(t, 0) + e.quantity
                matched = True
                break
        if not matched:
            type_count["Other"] = type_count.get("Other", 0) + e.quantity

    # Condition
    condition_count = {}
    condition_value = {}
    for e in entries:
        c = e.condition or "Unknown"
        condition_count[c] = condition_count.get(c, 0) + e.quantity
        condition_value[c] = condition_value.get(c, 0) + entry_value(e)

    # Foil
    foil_count   = sum(e.quantity for e in entries if e.foil)
    normal_count = sum(e.quantity for e in entries if not e.foil)
    foil_value   = sum(entry_value(e) for e in entries if e.foil)
    normal_value = sum(entry_value(e) for e in entries if not e.foil)

    # Top 10 most valuable individual entries
    top10 = sorted(entries, key=entry_value, reverse=True)[:10]
    top_cards = [
        {
            "name":             e.card.name,
            "set_name":         e.card.set_name,
            "set_code":         e.card.set_code,
            "collector_number": e.card.collector_number,
            "image_uri":        e.card.image_uri,
            "quantity":         e.quantity,
            "foil":             e.foil,
            "condition":        e.condition,
            "price_usd":        e.card.price_usd_foil if e.foil and e.card.price_usd_foil else e.card.price_usd,
            "total_value":      round(entry_value(e), 2),
        }
        for e in top10
    ]

    # Top 5 sets by card count
    set_count = {}
    set_names = {}
    for e in entries:
        set_count[e.card.set_code] = set_count.get(e.card.set_code, 0) + e.quantity
        set_names[e.card.set_code] = e.card.set_name
    top_sets = sorted(set_count.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "summary": {
            "total_cards":       total_cards,
            "unique_cards":      unique_cards,
            "total_value":       round(total_value, 2),
            "sets_represented":  len(sets),
            "foil_count":        foil_count,
            "normal_count":      normal_count,
            "foil_value":        round(foil_value, 2),
            "normal_value":      round(normal_value, 2),
        },
        "rarity":     [{"name": k, "count": v, "value": round(rarity_value[k], 2)} for k, v in sorted(rarity_count.items())],
        "colors":     [{"name": k, "count": v} for k, v in sorted(color_count.items(), key=lambda x: x[1], reverse=True)],
        "types":      [{"name": k, "count": v} for k, v in sorted(type_count.items(), key=lambda x: x[1], reverse=True)],
        "conditions": [{"name": k, "count": v, "value": round(condition_value[k], 2)} for k, v in sorted(condition_count.items())],
        "top_cards":  top_cards,
        "top_sets":   [{"set_code": k, "set_name": set_names[k], "count": v} for k, v in top_sets],
    }

class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


class ImportRequest(BaseModel):
    list_text: str
    condition: str = "NM"
    foil: bool = False


@router.post("/import", response_model=ImportResult)
def import_collection(
    payload: ImportRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Import cards from a Moxfield/MTGO format list.
    Accepted formats per line:
      4 Lightning Bolt (CLU) 141
      4 Lightning Bolt (CLU)
      4 Lightning Bolt
      1x Lightning Bolt
    """
    import re

    lines = [l.strip() for l in payload.list_text.strip().splitlines()]
    lines = [l for l in lines if l and not l.startswith('#')]

    imported = 0
    skipped = 0
    errors = []

    for line in lines:
        # Skip section headers like "Sideboard", "Commander", "Maindeck" etc.
        if re.match(r'^(Sideboard|Commander|Mainboard|Maindeck|Deck|Land|Creature|Instant|Sorcery|Enchantment|Artifact|Planeswalker)s?$', line, re.IGNORECASE):
            continue

        # Parse: quantity name (set) collector_number
        match = re.match(
            r'^(\d+)x?\s+(.+?)(?:\s+\(([A-Z0-9]{2,6})\)(?:\s+(\S+))?)?$',
            line,
            re.IGNORECASE,
        )

        if not match:
            errors.append(f'Could not parse: "{line}"')
            skipped += 1
            continue

        quantity   = int(match.group(1))
        name       = match.group(2).strip()
        set_code   = match.group(3)
        col_number = match.group(4)

        try:
            card = None

            # Try exact set + collector number lookup first (most precise)
            if set_code and col_number:
                with httpx.Client() as client:
                    r = client.get(
                        f"https://api.scryfall.com/cards/{set_code.lower()}/{col_number}",
                        timeout=10,
                    )
                if r.status_code == 200:
                    card = scryfall_service._upsert_card(db, r.json())

            # Fall back to fuzzy name search
            if not card:
                card = scryfall_service.get_card_by_name(name, db)

            if not card:
                errors.append(f'Card not found: "{name}"')
                skipped += 1
                continue

            # Check if entry already exists
            existing = (
                db.query(models.CollectionEntry)
                .filter(
                    models.CollectionEntry.user_id == current_user.id,
                    models.CollectionEntry.card_id == card.id,
                    models.CollectionEntry.foil == payload.foil,
                    models.CollectionEntry.condition == payload.condition,
                    models.CollectionEntry.language == "en",
                )
                .first()
            )

            if existing:
                existing.quantity += quantity
                db.commit()
            else:
                entry = models.CollectionEntry(
                    user_id=current_user.id,
                    card_id=card.id,
                    quantity=quantity,
                    foil=payload.foil,
                    condition=payload.condition,
                    language="en",
                )
                db.add(entry)
                db.commit()

            imported += 1

        except Exception as e:
            errors.append(f'Error importing "{name}": {str(e)}')
            skipped += 1
            continue

    return {"imported": imported, "skipped": skipped, "errors": errors}

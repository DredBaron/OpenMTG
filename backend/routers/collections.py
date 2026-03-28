from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload
from database import get_db
from security import get_current_user
from pydantic import BaseModel
from schemas import AddCardRequest, UpdateCardRequest, ImportResult, ImportRequest

import httpx
import models
import schemas
import services.scryfall as scryfall_service


router = APIRouter(prefix="/collection", tags=["collection"])


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
    if payload.is_favorite is not None:
        entry.is_favorite = payload.is_favorite

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

    uid = current_user.id

    price_expr = case(
        (
            (models.CollectionEntry.foil == True) &
            (models.Card.price_usd_foil != None),
            models.Card.price_usd_foil,
        ),
        else_=models.Card.price_usd,
    )
    multiplier_expr = case(
        (models.CollectionEntry.condition == "NM",  1.0),
        (models.CollectionEntry.condition == "LP",  0.75),
        (models.CollectionEntry.condition == "MP",  0.50),
        (models.CollectionEntry.condition == "HP",  0.25),
        (models.CollectionEntry.condition == "DMG", 0.10),
        else_=1.0,
    )
    value_expr = (
        func.coalesce(price_expr, 0.0)
        * models.CollectionEntry.quantity
        * multiplier_expr
    )

    total_cards, unique_cards = db.query(
        func.sum(models.CollectionEntry.quantity),
        func.count(models.CollectionEntry.id),
    ).filter(models.CollectionEntry.user_id == uid).one()

    if not unique_cards:
        return {}

    sets_represented = (
        db.query(func.count(func.distinct(models.Card.set_code)))
        .select_from(models.CollectionEntry)
        .join(models.CollectionEntry.card)
        .filter(models.CollectionEntry.user_id == uid)
        .scalar()
    )

    total_value = (
        db.query(func.sum(value_expr))
        .select_from(models.CollectionEntry)
        .join(models.CollectionEntry.card)
        .filter(models.CollectionEntry.user_id == uid)
        .scalar() or 0.0
    )

    rarity_rows = (
        db.query(
            models.Card.rarity,
            func.sum(models.CollectionEntry.quantity).label("count"),
            func.sum(value_expr).label("value"),
        )
        .select_from(models.CollectionEntry)
        .join(models.CollectionEntry.card)
        .filter(models.CollectionEntry.user_id == uid)
        .group_by(models.Card.rarity)
        .all()
    )

    condition_rows = (
        db.query(
            models.CollectionEntry.condition,
            func.sum(models.CollectionEntry.quantity).label("count"),
            func.sum(value_expr).label("value"),
        )
        .select_from(models.CollectionEntry)
        .join(models.CollectionEntry.card)
        .filter(models.CollectionEntry.user_id == uid)
        .group_by(models.CollectionEntry.condition)
        .all()
    )

    foil_rows = (
        db.query(
            models.CollectionEntry.foil,
            func.sum(models.CollectionEntry.quantity).label("count"),
            func.sum(value_expr).label("value"),
        )
        .select_from(models.CollectionEntry)
        .join(models.CollectionEntry.card)
        .filter(models.CollectionEntry.user_id == uid)
        .group_by(models.CollectionEntry.foil)
        .all()
    )

    foil_count = normal_count = 0
    foil_value = normal_value = 0.0
    for row in foil_rows:
        if row.foil:
            foil_count = row.count
            foil_value = row.value or 0.0
        else:
            normal_count = row.count
            normal_value = row.value or 0.0

    top_sets = (
        db.query(
            models.Card.set_code,
            models.Card.set_name,
            func.sum(models.CollectionEntry.quantity).label("count"),
        )
        .select_from(models.CollectionEntry)
        .join(models.CollectionEntry.card)
        .filter(models.CollectionEntry.user_id == uid)
        .group_by(models.Card.set_code, models.Card.set_name)
        .order_by(func.sum(models.CollectionEntry.quantity).desc())
        .limit(5)
        .all()
    )

    color_rows = (
        db.query(models.Card.color_identity, models.CollectionEntry.quantity)
        .select_from(models.CollectionEntry)
        .join(models.CollectionEntry.card)
        .filter(models.CollectionEntry.user_id == uid)
        .all()
    )
    color_count = {}
    for color_identity, quantity in color_rows:
        colors = color_identity or ""
        if not colors:
            color_count["Colorless"] = color_count.get("Colorless", 0) + quantity
        else:
            for c in colors:
                name = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}.get(c, c)
                color_count[name] = color_count.get(name, 0) + quantity

    type_rows = (
        db.query(models.Card.type_line, models.CollectionEntry.quantity)
        .select_from(models.CollectionEntry)
        .join(models.CollectionEntry.card)
        .filter(models.CollectionEntry.user_id == uid)
        .all()
    )
    type_count = {}
    type_keywords = ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land", "Battle"]
    for type_line, quantity in type_rows:
        tl = type_line or ""
        matched = False
        for t in type_keywords:
            if t in tl:
                type_count[t] = type_count.get(t, 0) + quantity
                matched = True
                break
        if not matched:
            type_count["Other"] = type_count.get("Other", 0) + quantity

    CONDITION_MULTIPLIERS = {
        "NM": 1.0,
        "LP": 0.75,
        "MP": 0.50,
        "HP": 0.25,
        "DMG": 0.1
    }

    top_card_rows = (
        db.query(
            models.Card.name,
            models.Card.set_name,
            models.Card.set_code,
            models.Card.collector_number,
            models.Card.image_uri,
            models.Card.price_usd,
            models.Card.price_usd_foil,
            models.CollectionEntry.quantity,
            models.CollectionEntry.foil,
            models.CollectionEntry.condition,
        )
        .select_from(models.CollectionEntry)
        .join(models.CollectionEntry.card)
        .filter(models.CollectionEntry.user_id == uid)
        .all()
    )

    def row_value(r):
        price = r.price_usd_foil if r.foil and r.price_usd_foil else r.price_usd
        return (price or 0) * r.quantity * CONDITION_MULTIPLIERS.get(r.condition, 1.0)

    top_cards = [
        {
            "name":             r.name,
            "set_name":         r.set_name,
            "set_code":         r.set_code,
            "collector_number": r.collector_number,
            "image_uri":        r.image_uri,
            "quantity":         r.quantity,
            "foil":             r.foil,
            "condition":        r.condition,
            "price_usd":        r.price_usd_foil if r.foil and r.price_usd_foil else r.price_usd,
            "total_value":      round(row_value(r), 2),
        }
        for r in sorted(top_card_rows, key=row_value, reverse=True)[:10]
    ]

    return {
        "summary": {
            "total_cards":      total_cards,
            "unique_cards":     unique_cards,
            "total_value":      round(total_value, 2),
            "sets_represented": sets_represented,
            "foil_count":       foil_count,
            "normal_count":     normal_count,
            "foil_value":       round(foil_value, 2),
            "normal_value":     round(normal_value, 2),
        },
        "rarity":     [{"name": r.rarity or "unknown", "count": r.count, "value": round(r.value or 0, 2)} for r in sorted(rarity_rows, key=lambda r: r.rarity or "")],
        "colors":     [{"name": k, "count": v} for k, v in sorted(color_count.items(), key=lambda x: x[1], reverse=True)],
        "types":      [{"name": k, "count": v} for k, v in sorted(type_count.items(), key=lambda x: x[1], reverse=True)],
        "conditions": [{"name": r.condition or "Unknown", "count": r.count, "value": round(r.value or 0, 2)} for r in sorted(condition_rows, key=lambda r: r.condition or "")],
        "top_cards":  top_cards,
        "top_sets":   [{"set_code": r.set_code, "set_name": r.set_name, "count": r.count} for r in top_sets],
    }

@router.post("/import", response_model=ImportResult)
def import_collection(
    payload: ImportRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    
    import re

    lines = [l.strip() for l in payload.list_text.strip().splitlines()]
    lines = [l for l in lines if l and not l.startswith('#')]

    imported = 0
    skipped = 0
    errors = []

    for line in lines:
        if re.match(r'^(Sideboard|Commander|Mainboard|Maindeck|Deck|Land|Creature|Instant|Sorcery|Enchantment|Artifact|Planeswalker)s?$', line, re.IGNORECASE):
            continue

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

            if set_code and col_number:
                with httpx.Client() as client:
                    r = client.get(
                        f"https://api.scryfall.com/cards/{set_code.lower()}/{col_number}",
                        timeout=10,
                    )
                if r.status_code == 200:
                    card = scryfall_service._upsert_card(db, r.json())

            if not card:
                card = scryfall_service.get_card_by_name(name, db)

            if not card:
                errors.append(f'Card not found: "{name}"')
                skipped += 1
                continue

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

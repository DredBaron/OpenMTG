from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from security import get_current_user
import schemas
import services.scryfall as scryfall_service
from services.scryfall_queue import scryfall_queue, Priority
import models

SCRYFALL_SEARCH = "https://api.scryfall.com/cards/search"

router = APIRouter(
    prefix="/cards",
    tags=["cards"],
    dependencies=[Depends(get_current_user)],
)


def _db_card_to_dict(c: models.Card) -> dict:
    return {
        "scryfall_id": c.scryfall_id,
        "name":        c.name,
        "set_code":    c.set_code,
        "set_name":    c.set_name,
        "mana_cost":   c.mana_cost,
        "type_line":   c.type_line,
        "rarity":      c.rarity,
        "colors":      list(c.colors) if c.colors else [],
        "price_usd":   c.price_usd,
    }


def _scryfall_card_to_dict(c: dict) -> dict:
    return {
        "scryfall_id": c["id"],
        "name":        c["name"],
        "set_code":    c["set"],
        "set_name":    c.get("set_name"),
        "mana_cost":   c.get("mana_cost", ""),
        "type_line":   c.get("type_line", ""),
        "rarity":      c.get("rarity", ""),
        "colors":      c.get("colors", []),
        "price_usd":   float(c["prices"]["usd"]) if c.get("prices", {}).get("usd") else None,
    }


@router.get("/search", response_model=list[schemas.CardOut])
def search(
    q: str = Query(..., min_length=2, description="Scryfall search query"),
    db: Session = Depends(get_db),
):
    try:
        return scryfall_service.search_cards(q, db)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scryfall error: {str(e)}")


@router.get("/named", response_model=schemas.CardOut)
def get_by_name(
    name: str = Query(..., description="Card name (fuzzy match)"),
    db: Session = Depends(get_db),
):
    card = scryfall_service.get_card_by_name(name, db)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@router.get("/collection/search")
def search_collection(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(models.Card)
        .join(models.CollectionEntry, models.CollectionEntry.card_id == models.Card.id)
        .filter(
            models.CollectionEntry.user_id == current_user.id,
            models.Card.name.ilike(f"%{q}%"),
        )
        .distinct()
        .order_by(models.Card.name)
        .limit(25)
        .all()
    )
    return [_db_card_to_dict(c) for c in rows]


@router.get("/scryfall/search")
def scryfall_search(q: str):
    r = scryfall_queue.get(
        SCRYFALL_SEARCH,
        params={"q": q, "unique": "cards", "order": "name"},
        priority=Priority.USER,
    )
    if r is None:
        raise HTTPException(status_code=502, detail="Scryfall search failed")
    if r.status_code == 404:
        return []
    if not r.is_success:
        raise HTTPException(status_code=502, detail="Scryfall search failed")
 
    return [_scryfall_card_to_dict(c) for c in r.json().get("data", [])[:25]]



@router.get("/printings")
def get_printings_by_name(
    name:       str     = Query(...),
    owned_only: bool    = True,
    db:         Session = Depends(get_db),
):
    if owned_only:
        rows = (
            db.query(models.Card)
            .filter(models.Card.name == name)
            .order_by(models.Card.set_code)
            .all()
        )
        return [_db_card_to_dict(c) for c in rows]
 
    r = scryfall_queue.get(
        SCRYFALL_SEARCH,
        params={
            "q":      f'!"{name}"',
            "unique": "prints",
            "order":  "released",
            "dir":    "desc",
        },
        priority=Priority.USER,
    )
    if r is None:
        raise HTTPException(status_code=502, detail="Scryfall fetch failed")
    if not r.is_success:
        raise HTTPException(status_code=502, detail="Scryfall fetch failed")
 
    return [_scryfall_card_to_dict(c) for c in r.json().get("data", [])]



@router.get("/{scryfall_id}", response_model=schemas.CardOut)
def get_by_id(
    scryfall_id: str,
    db: Session = Depends(get_db),
):
    card = scryfall_service.get_card_by_scryfall_id(scryfall_id, db)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@router.get("/{scryfall_id}/printings")
def get_printings(
    scryfall_id: str,
    db: Session = Depends(get_db),
):
    card = scryfall_service.get_card_by_scryfall_id(scryfall_id, db)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    try:
        printings = scryfall_service.get_card_printings(card.name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scryfall error: {str(e)}")
    return printings

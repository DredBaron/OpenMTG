import json
import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session, joinedload
from database import get_db
from security import get_current_user
import models

router = APIRouter(prefix="/export", tags=["export"])


def _collection_to_rows(entries: list) -> list[dict]:
    """Flatten collection entries into simple dicts for export."""
    return [
        {
            "name":             e.card.name,
            "scryfall_id":      e.card.scryfall_id,
            "set_code":         e.card.set_code,
            "set_name":         e.card.set_name,
            "collector_number": e.card.collector_number,
            "rarity":           e.card.rarity,
            "type_line":        e.card.type_line,
            "mana_cost":        e.card.mana_cost,
            "quantity":         e.quantity,
            "foil":             e.foil,
            "condition":        e.condition,
            "language":         e.language,
            "notes":            e.notes or "",
            "price_usd":        e.card.price_usd,
            "price_usd_foil":   e.card.price_usd_foil,
        }
        for e in entries
    ]


def _deck_to_rows(deck_cards: list) -> list[dict]:
    return [
        {
            "name":             dc.card.name,
            "scryfall_id":      dc.card.scryfall_id,
            "set_code":         dc.card.set_code,
            "collector_number": dc.card.collector_number,
            "quantity":         dc.quantity,
            "is_sideboard":     dc.is_sideboard,
            "is_commander":     dc.is_commander,
            "mana_cost":        dc.card.mana_cost,
            "type_line":        dc.card.type_line,
            "price_usd":        dc.card.price_usd,
        }
        for dc in deck_cards
    ]


def _rows_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _rows_to_sql(rows: list[dict], table: str) -> str:
    if not rows:
        return f"-- No data in {table}\n"
    lines = [f"-- Export from OpenMTG: {table}\n"]
    for row in rows:
        cols = ", ".join(row.keys())
        vals = ", ".join(
            "NULL" if v is None
            else f"'{str(v).replace(chr(39), chr(39)*2)}'"  # escape single quotes
            for v in row.values()
        )
        lines.append(f"INSERT INTO {table} ({cols}) VALUES ({vals});")
    return "\n".join(lines)


def _rows_to_moxfield(rows: list[dict]) -> str:
    """
    Moxfield/MTGO format: '4 Lightning Bolt (CLU) 141'
    Widely accepted by Moxfield, Archidekt, CubeCobra, etc.
    """
    lines = []
    main = [r for r in rows if not r.get("is_sideboard") and not r.get("is_commander")]
    side = [r for r in rows if r.get("is_sideboard")]
    cmdr = [r for r in rows if r.get("is_commander")]

    for r in cmdr:
        lines.append(f"Commander\n1 {r['name']} ({r['set_code'].upper()}) {r['collector_number']}")
    if cmdr:
        lines.append("")

    for r in main:
        lines.append(f"{r['quantity']} {r['name']} ({r['set_code'].upper()}) {r['collector_number']}")

    if side:
        lines.append("\nSideboard")
        for r in side:
            lines.append(f"{r['quantity']} {r['name']} ({r['set_code'].upper()}) {r['collector_number']}")

    return "\n".join(lines)


def _stream(content: str, filename: str, media_type: str) -> StreamingResponse:
    return StreamingResponse(
        io.StringIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# Collection exports

@router.get("/collection/json")
def export_collection_json(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entries = (
        db.query(models.CollectionEntry)
        .options(joinedload(models.CollectionEntry.card))
        .filter(models.CollectionEntry.user_id == current_user.id)
        .all()
    )
    rows = _collection_to_rows(entries)
    content = json.dumps(rows, indent=2, default=str)
    return _stream(content, "collection.json", "application/json")


@router.get("/collection/csv")
def export_collection_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entries = (
        db.query(models.CollectionEntry)
        .options(joinedload(models.CollectionEntry.card))
        .filter(models.CollectionEntry.user_id == current_user.id)
        .all()
    )
    content = _rows_to_csv(_collection_to_rows(entries))
    return _stream(content, "collection.csv", "text/csv")


@router.get("/collection/sql")
def export_collection_sql(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    entries = (
        db.query(models.CollectionEntry)
        .options(joinedload(models.CollectionEntry.card))
        .filter(models.CollectionEntry.user_id == current_user.id)
        .all()
    )
    content = _rows_to_sql(_collection_to_rows(entries), "collection")
    return _stream(content, "collection.sql", "text/plain")


# Deck exports

@router.get("/deck/{deck_id}/json")
def export_deck_json(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    deck = db.query(models.Deck).filter(
        models.Deck.id == deck_id,
        models.Deck.user_id == current_user.id,
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    deck_cards = (
        db.query(models.DeckCard)
        .options(joinedload(models.DeckCard.card))
        .filter(models.DeckCard.deck_id == deck_id)
        .all()
    )
    rows = _deck_to_rows(deck_cards)
    content = json.dumps({"deck": deck.name, "format": deck.format, "cards": rows},
                         indent=2, default=str)
    return _stream(content, f"deck_{deck_id}.json", "application/json")


@router.get("/deck/{deck_id}/csv")
def export_deck_csv(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    deck = db.query(models.Deck).filter(
        models.Deck.id == deck_id,
        models.Deck.user_id == current_user.id,
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    deck_cards = (
        db.query(models.DeckCard)
        .options(joinedload(models.DeckCard.card))
        .filter(models.DeckCard.deck_id == deck_id)
        .all()
    )
    content = _rows_to_csv(_deck_to_rows(deck_cards))
    return _stream(content, f"deck_{deck_id}.csv", "text/csv")


@router.get("/deck/{deck_id}/moxfield")
def export_deck_moxfield(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Export in the format accepted by Moxfield, Archidekt, CubeCobra, MTGO."""
    deck = db.query(models.Deck).filter(
        models.Deck.id == deck_id,
        models.Deck.user_id == current_user.id,
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    deck_cards = (
        db.query(models.DeckCard)
        .options(joinedload(models.DeckCard.card))
        .filter(models.DeckCard.deck_id == deck_id)
        .all()
    )
    content = _rows_to_moxfield(_deck_to_rows(deck_cards))
    return _stream(content, f"deck_{deck_id}.txt", "text/plain")

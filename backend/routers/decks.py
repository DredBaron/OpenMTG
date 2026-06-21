from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from database import get_db, SessionLocal
from security import get_current_user
import json
import re
import models
import schemas
import services.scryfall as scryfall_service
from schemas import CreateDeckRequest, UpdateDeckRequest, AddDeckCardRequest, UpdateDeckCardRequest
from services.scryfall_queue import scryfall_queue, Priority


router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("", response_model=list[schemas.DeckOut])
def list_decks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    raw = (
        db.query(models.Deck)
        .options(joinedload(models.Deck.cards).joinedload(models.DeckCard.card))
        .filter(models.Deck.user_id == current_user.id)
        .order_by(models.Deck.created_at.desc())
        .all()
    )
    result = []
    for deck in raw:
        commanders = [dc for dc in deck.cards if dc.is_commander]
        mainboard = [dc for dc in deck.cards if not dc.is_sideboard and not dc.is_commander]
        preview_cards = [
            schemas.DeckPreviewCard(scryfall_id=dc.card.scryfall_id, is_commander=True)
            for dc in commanders if dc.card.scryfall_id
        ] + [
            schemas.DeckPreviewCard(scryfall_id=dc.card.scryfall_id, is_commander=False)
            for dc in mainboard if dc.card.scryfall_id
        ]
        result.append(schemas.DeckOut(
            id=deck.id,
            name=deck.name,
            format=deck.format,
            description=deck.description,
            is_public=deck.is_public,
            created_at=deck.created_at,
            card_count=sum(dc.quantity for dc in mainboard),
            preview_cards=preview_cards,
        ))
    return result


@router.post("", response_model=schemas.DeckOut, status_code=201)
def create_deck(
    payload: CreateDeckRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    deck = models.Deck(
        user_id=current_user.id,
        name=payload.name,
        format=payload.format,
        description=payload.description,
        is_public=payload.is_public,
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck


@router.post("/import")
def import_deck(
    payload: schemas.DeckImportRequest,
    current_user: models.User = Depends(get_current_user),
    _db: Session = Depends(get_db),
):
    user_id = current_user.id
    name = payload.name
    fmt = payload.format
    description = payload.description
    list_text = payload.list_text

    SECTION_RE = re.compile(
        r'^(Commander|Sideboard|Mainboard|Maindeck|Main|Deck)s?$',
        re.IGNORECASE,
    )
    CARD_RE = re.compile(
        r'^(\d+)x?\s+(.+?)(?:\s+\(([A-Z0-9]{2,6})\)(?:\s+(\S+))?)?$',
        re.IGNORECASE,
    )

    def generate():
        db = SessionLocal()
        try:
            deck = models.Deck(
                user_id=user_id,
                name=name,
                format=fmt,
                description=description,
            )
            db.add(deck)
            db.commit()
            db.refresh(deck)

            lines = [l.strip() for l in list_text.strip().splitlines()]
            card_lines = [
                l for l in lines
                if l and not l.startswith('#') and not SECTION_RE.match(l) and CARD_RE.match(l)
            ]
            total = len(card_lines)

            yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"

            imported = 0
            skipped = 0
            errors = []
            is_commander = False
            is_sideboard = False
            done = 0

            for line in lines:
                if not line or line.startswith('#'):
                    continue

                section = SECTION_RE.match(line)
                if section:
                    key = section.group(1).lower()
                    is_commander = key == 'commander'
                    is_sideboard = key == 'sideboard'
                    continue

                m = CARD_RE.match(line)
                if not m:
                    errors.append(f'Could not parse: "{line}"')
                    skipped += 1
                    done += 1
                    yield f"data: {json.dumps({'type': 'progress', 'done': done, 'total': total, 'card': ''})}\n\n"
                    continue

                quantity   = 1 if is_commander else int(m.group(1))
                card_name  = m.group(2).strip()
                set_code   = m.group(3)
                col_number = m.group(4)

                yield f"data: {json.dumps({'type': 'progress', 'done': done, 'total': total, 'card': card_name})}\n\n"

                try:
                    card = None
                    if set_code and col_number:
                        url = f"https://api.scryfall.com/cards/{set_code.lower()}/{col_number}"
                        r = scryfall_queue.get(url, priority=Priority.USER)
                        if r is not None and r.status_code == 200:
                            card = scryfall_service._upsert_card(db, r.json())
                    if not card:
                        card = scryfall_service.get_card_by_name(card_name, db)
                    if not card:
                        errors.append(f'Card not found: "{card_name}"')
                        skipped += 1
                    else:
                        existing = db.query(models.DeckCard).filter(
                            models.DeckCard.deck_id == deck.id,
                            models.DeckCard.card_id == card.id,
                            models.DeckCard.is_sideboard == is_sideboard,
                            models.DeckCard.is_commander == is_commander,
                        ).first()
                        if existing:
                            existing.quantity += quantity
                        else:
                            db.add(models.DeckCard(
                                deck_id=deck.id,
                                card_id=card.id,
                                quantity=quantity,
                                is_sideboard=is_sideboard,
                                is_commander=is_commander,
                            ))
                        db.commit()
                        imported += 1
                except Exception as e:
                    errors.append(f'Error importing "{card_name}": {str(e)}')
                    skipped += 1

                done += 1

            yield f"data: {json.dumps({'type': 'done', 'deck_id': deck.id, 'deck_name': deck.name, 'imported': imported, 'skipped': skipped, 'errors': errors})}\n\n"

        finally:
            db.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/{deck_id}", response_model=schemas.DeckDetailOut)
def get_deck(
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    deck = (
        db.query(models.Deck)
        .options(
            joinedload(models.Deck.cards).joinedload(models.DeckCard.card)
        )
        .filter(models.Deck.id == deck_id)
        .first()
    )
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    if deck.user_id != current_user.id and not deck.is_public:
        raise HTTPException(status_code=403, detail="Access denied")
    return deck


@router.patch("/{deck_id}", response_model=schemas.DeckOut)
def update_deck(
    deck_id: int,
    payload: UpdateDeckRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    deck = db.query(models.Deck).filter(
        models.Deck.id == deck_id,
        models.Deck.user_id == current_user.id,
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    if payload.name is not None:
        deck.name = payload.name
    if payload.format is not None:
        deck.format = payload.format
    if payload.description is not None:
        deck.description = payload.description
    if payload.is_public is not None:
        deck.is_public = payload.is_public

    db.commit()
    db.refresh(deck)
    return deck


@router.delete("/{deck_id}", status_code=204)
def delete_deck(
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
    db.delete(deck)
    db.commit()


@router.post("/{deck_id}/cards", response_model=schemas.DeckCardOut, status_code=201)
def add_card_to_deck(
    deck_id: int,
    payload: AddDeckCardRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    deck = db.query(models.Deck).filter(
        models.Deck.id == deck_id,
        models.Deck.user_id == current_user.id,
    ).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    card = scryfall_service.get_card_by_scryfall_id(payload.scryfall_id, db)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found on Scryfall")

    existing = db.query(models.DeckCard).filter(
        models.DeckCard.deck_id == deck_id,
        models.DeckCard.card_id == card.id,
        models.DeckCard.is_sideboard == payload.is_sideboard,
        models.DeckCard.is_commander == payload.is_commander,
    ).first()

    if existing:
        existing.quantity += payload.quantity
        db.commit()
        db.refresh(existing)
        response.status_code = status.HTTP_200_OK
        return existing

    deck_card = models.DeckCard(
        deck_id=deck_id,
        card_id=card.id,
        quantity=payload.quantity,
        is_sideboard=payload.is_sideboard,
        is_commander=payload.is_commander,
    )
    db.add(deck_card)
    db.commit()
    db.refresh(deck_card)
    return deck_card


@router.patch("/{deck_id}/cards/{deck_card_id}", response_model=schemas.DeckCardOut)
def update_deck_card(
    deck_id: int,
    deck_card_id: int,
    payload: UpdateDeckCardRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    deck_card = (
        db.query(models.DeckCard)
        .join(models.Deck)
        .filter(
            models.DeckCard.id == deck_card_id,
            models.DeckCard.deck_id == deck_id,
            models.Deck.user_id == current_user.id,
        )
        .first()
    )
    if not deck_card:
        raise HTTPException(status_code=404, detail="Card not found in deck")

    if payload.quantity is not None:
        deck_card.quantity = payload.quantity
    if payload.is_sideboard is not None:
        deck_card.is_sideboard = payload.is_sideboard
    if payload.is_commander is not None:
        deck_card.is_commander = payload.is_commander
    if payload.scryfall_id is not None:
        card = scryfall_service.get_card_by_scryfall_id(payload.scryfall_id, db)
        if not card:
            raise HTTPException(status_code=404, detail="Card not found on Scryfall")
        deck_card.card_id = card.id

    db.commit()
    db.refresh(deck_card)
    return deck_card


@router.delete("/{deck_id}/cards/{deck_card_id}", status_code=204)
def remove_card_from_deck(
    deck_id: int,
    deck_card_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    deck_card = (
        db.query(models.DeckCard)
        .join(models.Deck)
        .filter(
            models.DeckCard.id == deck_card_id,
            models.DeckCard.deck_id == deck_id,
            models.Deck.user_id == current_user.id,
        )
        .first()
    )
    if not deck_card:
        raise HTTPException(status_code=404, detail="Card not found in deck")

    db.delete(deck_card)
    db.commit()

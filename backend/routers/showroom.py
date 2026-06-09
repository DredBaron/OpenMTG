from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from database import get_db
import models
import schemas

router = APIRouter(prefix="/showroom", tags=["showroom"])


@router.get("/display/{username}", response_model=schemas.ShowroomOut)
def get_showroom(username: str, db: Session = Depends(get_db)):
    slug = username.lower()
    user = db.query(models.User).filter(func.lower(models.User.username) == slug).first()
    if not user:
        raise HTTPException(status_code=404, detail="Showroom not found")

    raw_decks = (
        db.query(models.Deck)
        .options(joinedload(models.Deck.cards).joinedload(models.DeckCard.card))
        .filter(models.Deck.user_id == user.id, models.Deck.is_public == True)
        .order_by(models.Deck.name)
        .all()
    )

    decks = []
    for deck in raw_decks:
        commanders = [dc for dc in deck.cards if dc.is_commander]
        mainboard = [dc for dc in deck.cards if not dc.is_sideboard and not dc.is_commander]
        card_count = sum(dc.quantity for dc in mainboard)
        preview_cards = [
            schemas.ShowroomPreviewCard(scryfall_id=dc.card.scryfall_id, is_commander=True)
            for dc in commanders if dc.card.scryfall_id
        ] + [
            schemas.ShowroomPreviewCard(scryfall_id=dc.card.scryfall_id, is_commander=False)
            for dc in mainboard if dc.card.scryfall_id
        ]
        decks.append(schemas.ShowroomDeckOut(
            id=deck.id,
            name=deck.name,
            format=deck.format,
            description=deck.description,
            card_count=card_count,
            preview_cards=preview_cards,
        ))

    raw_cards = (
        db.query(models.CollectionEntry)
        .options(joinedload(models.CollectionEntry.card))
        .filter(
            models.CollectionEntry.user_id == user.id,
            models.CollectionEntry.in_showroom == True,
        )
        .all()
    )

    cards = [
        schemas.ShowroomCardOut(
            id=entry.id,
            name=entry.card.name,
            image_uri=entry.card.image_uri,
            foil=entry.foil,
        )
        for entry in raw_cards
    ]

    return schemas.ShowroomOut(decks=decks, cards=cards)

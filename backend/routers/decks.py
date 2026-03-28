# backend/routers/decks.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
from security import get_current_user
import models
import schemas
import services.scryfall as scryfall_service
from pydantic import BaseModel
from schemas import CreateDeckRequest, UpdateDeckRequest, AddDeckCardRequest, UpdateDeckCardRequest


router = APIRouter(prefix="/decks", tags=["decks"])


# --- Deck CRUD ---

@router.get("", response_model=list[schemas.DeckOut])
def list_decks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Deck)
        .filter(models.Deck.user_id == current_user.id)
        .order_by(models.Deck.created_at.desc())
        .all()
    )


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


# --- Cards within a deck ---

@router.post("/{deck_id}/cards", response_model=schemas.DeckCardOut, status_code=201)
def add_card_to_deck(
    deck_id: int,
    payload: AddDeckCardRequest,
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
    ).first()

    if existing:
        existing.quantity += payload.quantity
        db.commit()
        db.refresh(existing)
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

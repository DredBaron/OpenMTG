from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from security import get_current_user
import schemas
import services.scryfall as scryfall_service

router = APIRouter(
    prefix="/cards",
    tags=["cards"],
    dependencies=[Depends(get_current_user)],
)


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
    """Get all set printings for a card by its Scryfall ID."""
    card = scryfall_service.get_card_by_scryfall_id(scryfall_id, db)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    try:
        printings = scryfall_service.get_card_printings(card.name)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Scryfall error: {str(e)}")
    return printings

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import services.settings as settings_service

router = APIRouter(prefix="/card-search", tags=["card-search"])


@router.get("/status")
def card_search_status(db: Session = Depends(get_db)):
    return {"enabled": settings_service.get(db, "card_search_enabled") != "false"}

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from security import get_current_user
import models
import services.settings as settings_service
import services.price_refresh as refresh_service
import threading
from schemas import SettingsUpdate

def require_admin(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


router = APIRouter(
    prefix="/admin/settings",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    return settings_service.get_all(db)


@router.patch("")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    if payload.price_refresh_hours is not None:
        if not 1 <= payload.price_refresh_hours <= 8760:
            raise HTTPException(status_code=400, detail="Refresh hours must be between 1 and 8760")
        settings_service.set_value(db, "price_refresh_hours", str(payload.price_refresh_hours))

    if payload.scryfall_rps is not None:
        if not 1 <= payload.scryfall_rps <= 10:
            raise HTTPException(status_code=400, detail="Requests per second must be between 1 and 10")
        settings_service.set_value(db, "scryfall_rps", str(payload.scryfall_rps))

    return settings_service.get_all(db)


@router.post("/refresh-now")
def trigger_refresh(db: Session = Depends(get_db)):
    card_count = db.query(models.Card).count()
    if card_count == 0:
        raise HTTPException(status_code=400, detail="No cards in cache to refresh")

    rps = settings_service.get_int(db, "scryfall_rps") or 1

    def run():
        from database import SessionLocal
        fresh_db = SessionLocal()
        try:
            refresh_service.refresh_card_prices(fresh_db, rps=float(rps))
        finally:
            fresh_db.close()

    threading.Thread(target=run, daemon=True).start()
    return {
        "message": f"Price refresh started for {card_count} cards at {rps} req/s",
        "card_count": card_count,
        "rps": rps,
    }


@router.get("/refresh-status")
def refresh_status(db: Session = Depends(get_db)):
    from datetime import datetime, timedelta

    total = db.query(models.Card).count()
    hours = settings_service.get_int(db, "price_refresh_hours")
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    stale = db.query(models.Card).filter(models.Card.last_fetched < cutoff).count()
    newest = db.query(models.Card).order_by(models.Card.last_fetched.desc()).first()
    oldest = db.query(models.Card).order_by(models.Card.last_fetched.asc()).first()

    return {
        "total_cards":   total,
        "stale_cards":   stale,
        "fresh_cards":   total - stale,
        "refresh_hours": hours,
        "oldest_fetch":  oldest.last_fetched.isoformat() if oldest else None,
        "newest_fetch":  newest.last_fetched.isoformat() if newest else None,
    }

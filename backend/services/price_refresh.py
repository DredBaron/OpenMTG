import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import services.settings as settings_service
from services.scryfall_queue import scryfall_queue, Priority

logger = logging.getLogger(__name__)


def _purge_old_history(db: Session) -> None:
    days = settings_service.get_int(db, "price_history_days")
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = (
        db.query(models.PriceHistory)
        .filter(models.PriceHistory.recorded_at < cutoff)
        .delete()
    )
    db.commit()
    if deleted:
        logger.info(f"Purged {deleted} price history rows older than {days} days")


def _record_price_history(db: Session, card: models.Card) -> None:
    snapshot = models.PriceHistory(
        card_id=card.id,
        price_usd=card.price_usd,
        price_usd_foil=card.price_usd_foil,
        price_eur=card.price_eur,
        price_eur_foil=card.price_eur_foil,
    )
    db.add(snapshot)


def refresh_card_prices(db: Session) -> None:
    cards = db.query(models.Card).all()
    if not cards:
        return
 
    logger.info(
        f"Starting price refresh for {len(cards)} cards "
        f"(BACKGROUND priority, 2 req/s via ScryfallQueue)"
    )
    updated = 0
    failed  = 0
 
    for card in cards:
        r = scryfall_queue.get(
            f"https://api.scryfall.com/cards/{card.scryfall_id}",
            priority=Priority.BACKGROUND,
        )
 
        if r is None or r.status_code != 200:
            failed += 1
            continue
 
        prices = r.json().get("prices", {})
        card.price_usd = float(prices["usd"]) if prices.get("usd")       else None
        card.price_usd_foil = float(prices["usd_foil"]) if prices.get("usd_foil")  else None
        card.price_eur = float(prices["eur"]) if prices.get("eur")       else None
        card.price_eur_foil = float(prices["eur_foil"]) if prices.get("eur_foil")  else None
        card.last_fetched = datetime.now(timezone.utc)
 
        _record_price_history(db, card)
        db.commit()
        updated += 1
 
    logger.info(f"Price refresh complete | {updated} updated, {failed} failed")
 
    try:
        _purge_old_history(db)
    except Exception as e:
        logger.warning(f"History purge failed (non-critical): {e}")


def should_refresh(db: Session) -> bool:
    hours = settings_service.get_int(db, "price_refresh_hours")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return db.query(models.Card).filter(models.Card.last_fetched < cutoff).first() is not None


def run_scheduler() -> None:
    logger.info("Price refresh scheduler started")
    time.sleep(10)
    while True:
        try:
            db = SessionLocal()
            try:
                if should_refresh(db):
                    refresh_card_prices(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        time.sleep(30 * 60)


def start_scheduler():
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    logger.info("Price refresh scheduler thread launched")

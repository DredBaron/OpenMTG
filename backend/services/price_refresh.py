import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import services.settings as settings_service
from markets import MARKETS
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
    fields = {"card_id": card.id}
    for currency in MARKETS:
        fields[f"price_{currency}"]      = getattr(card, f"price_{currency}", None)
        fields[f"price_{currency}_foil"] = getattr(card, f"price_{currency}_foil", None)
    db.add(models.PriceHistory(**fields))


def refresh_card_prices(db: Session) -> None:
    cards = db.query(models.Card).all()
    if not cards:
        return

    wishlist_ids = {
        row[0] for row in db.query(models.WishlistEntry.card_id).distinct().all()
    }
    priority_cards = [c for c in cards if c.id in wishlist_ids]
    other_cards    = [c for c in cards if c.id not in wishlist_ids]
    ordered_cards  = priority_cards + other_cards

    logger.info(
        f"Starting price refresh for {len(cards)} cards "
        f"({len(priority_cards)} wishlist-priority, BACKGROUND priority, 2 req/s via ScryfallQueue)"
    )
    updated = 0
    failed  = 0

    for card in ordered_cards:
        r = scryfall_queue.get(
            f"https://api.scryfall.com/cards/{card.scryfall_id}",
            priority=Priority.BACKGROUND,
        )

        if r is None or r.status_code != 200:
            failed += 1
            continue

        prices = r.json().get("prices", {})
        seen_adapters: set = set()
        for market in MARKETS.values():
            adapter = market.get("adapter")
            if adapter and adapter not in seen_adapters:
                for field, value in adapter.extract_prices(prices).items():
                    setattr(card, field, value)
                seen_adapters.add(adapter)

        card.last_fetched = datetime.now(timezone.utc)
        _record_price_history(db, card)
        db.commit()
        updated += 1

    logger.info(f"Price refresh complete | {updated} updated, {failed} failed")

    try:
        from services.exchange_rates import refresh_db_rates
        refresh_db_rates(db)
    except Exception as e:
        logger.warning(f"Exchange rate refresh failed (non-critical): {e}")

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

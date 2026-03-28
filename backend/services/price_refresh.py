import time
import logging
import threading
from datetime import datetime, timedelta
import httpx
_client = httpx.Client(timeout=10)
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import services.settings as settings_service

logger = logging.getLogger(__name__)

_last_request_time = 0.0
_rps_lock = threading.Lock()


def scryfall_get(url: str, params: dict = None, rps: float = 1.0) -> dict | None:
    global _last_request_time
    with _rps_lock:
        min_gap = 1.0 / rps
        now = time.monotonic()
        wait = min_gap - (now - _last_request_time)
        if wait > 0:
            time.sleep(wait)
        _last_request_time = time.monotonic()

    try:
        r = _client.get(url, params=params)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            logger.warning("Scryfall rate limit hit — backing off 60s")
            time.sleep(60)
        return None
    except Exception as e:
        logger.error(f"Scryfall request failed: {e}")
        return None


def refresh_card_prices(db: Session, rps: float = 1.0):
    cards = db.query(models.Card).all()
    if not cards:
        return

    logger.info(f"Starting price refresh for {len(cards)} cards at {rps} req/s")
    updated = 0
    failed = 0

    for card in cards:
        data = scryfall_get(
            f"https://api.scryfall.com/cards/{card.scryfall_id}",
            rps=rps,
        )
        if not data:
            failed += 1
            continue

        prices = data.get("prices", {})
        card.price_usd       = float(prices["usd"])       if prices.get("usd")       else None
        card.price_usd_foil  = float(prices["usd_foil"])  if prices.get("usd_foil")  else None
        card.price_eur       = float(prices["eur"])        if prices.get("eur")       else None
        card.last_fetched    = datetime.utcnow()
        db.commit()
        updated += 1

    logger.info(f"Price refresh complete — {updated} updated, {failed} failed")


def should_refresh(db: Session) -> bool:
    hours = settings_service.get_int(db, "price_refresh_hours")
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    stale = db.query(models.Card).filter(
        models.Card.last_fetched < cutoff
    ).first()
    return stale is not None


def run_scheduler():
    logger.info("Price refresh scheduler started")
    time.sleep(10)
    while True:
        try:
            db = SessionLocal()
            try:
                if should_refresh(db):
                    rps = settings_service.get_int(db, "scryfall_rps") or 1
                    refresh_card_prices(db, rps=float(rps))
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        time.sleep(30 * 60)


def start_scheduler():
    t = threading.Thread(target=run_scheduler, daemon=True)
    t.start()
    logger.info("Price refresh scheduler thread launched")

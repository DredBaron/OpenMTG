import time
import logging
import threading
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session, joinedload
from database import SessionLocal
import models
import services.settings as settings_service
import services.webhooks as webhooks
from markets import MARKETS, resolve_base_currency_and_rate
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


def _check_wishlist_targets(db: Session) -> None:
    entries = (
        db.query(models.WishlistEntry)
        .join(models.WishlistEntry.card)
        .options(joinedload(models.WishlistEntry.card), joinedload(models.WishlistEntry.owner))
        .filter(models.WishlistEntry.target_price.isnot(None))
        .all()
    )

    for entry in entries:
        owner = entry.owner
        card = entry.card
        if owner is None:
            continue

        currency = owner.preferred_currency or "usd"
        base_currency, rate, display_currency = resolve_base_currency_and_rate(db, currency)

        foil_price   = getattr(card, f"price_{base_currency}_foil", None)
        normal_price = getattr(card, f"price_{base_currency}", None)
        base_price   = foil_price if (entry.foil and foil_price is not None) else normal_price
        current_price = (base_price * rate) if base_price is not None else None

        met = current_price is not None and current_price <= entry.target_price
        if met and not entry.notified:
            webhooks.notify_wishlist_target_met(
                db, entry, round(current_price, 2), display_currency.upper()
            )
            entry.notified = True
        elif not met and entry.notified:
            entry.notified = False

    db.commit()


def _record_price_history(db: Session, card: models.Card) -> None:
    fields = {"card_id": card.id}
    for currency in MARKETS:
        fields[f"price_{currency}"]      = getattr(card, f"price_{currency}", None)
        fields[f"price_{currency}_foil"] = getattr(card, f"price_{currency}_foil", None)
    db.add(models.PriceHistory(**fields))


SCRYFALL_COLLECTION_URL = "https://api.scryfall.com/cards/collection"
BATCH_SIZE = 75


def refresh_card_prices(db: Session) -> None:
    wishlist_ids = {
        row[0] for row in db.query(models.WishlistEntry.card_id).distinct().all()
    }

    all_pairs = db.query(models.Card.id, models.Card.scryfall_id).all()
    if not all_pairs:
        return

    ordered = sorted(all_pairs, key=lambda p: (0 if p[0] in wishlist_ids else 1))

    n_wishlist = sum(1 for p in ordered if p[0] in wishlist_ids)
    n_batches  = (len(ordered) + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info(
        f"Starting price refresh for {len(ordered)} cards "
        f"({n_wishlist} wishlist-priority) in {n_batches} batch(es) of up to {BATCH_SIZE}"
    )

    updated = 0
    failed  = 0

    for i in range(0, len(ordered), BATCH_SIZE):
        batch = ordered[i:i + BATCH_SIZE]
        sid_to_dbid = {scryfall_id: card_id for card_id, scryfall_id in batch}

        r = scryfall_queue.post(
            SCRYFALL_COLLECTION_URL,
            body={"identifiers": [{"id": sid} for sid in sid_to_dbid]},
            priority=Priority.BACKGROUND,
        )

        if r is None or r.status_code != 200:
            failed += len(batch)
            logger.warning(
                f"Batch {i // BATCH_SIZE + 1}/{n_batches} failed: "
                f"{'timeout' if r is None else r.status_code}"
            )
            continue

        rdata = r.json()
        failed += len(rdata.get("not_found", []))

        cards_to_expunge = []
        for scryfall_data in rdata.get("data", []):
            card_id = sid_to_dbid.get(scryfall_data["id"])
            if card_id is None:
                continue
            card = db.get(models.Card, card_id)
            if card is None:
                continue

            prices = scryfall_data.get("prices", {})
            seen_adapters: set = set()
            for market in MARKETS.values():
                adapter = market.get("adapter")
                if adapter and adapter not in seen_adapters:
                    for field, value in adapter.extract_prices(prices).items():
                        setattr(card, field, value)
                    seen_adapters.add(adapter)

            card.last_fetched = datetime.now(timezone.utc)
            _record_price_history(db, card)
            cards_to_expunge.append(card)
            updated += 1

        db.commit()
        for card in cards_to_expunge:
            db.expunge(card)

    logger.info(f"Price refresh complete | {updated} updated, {failed} failed")

    try:
        from services.exchange_rates import refresh_db_rates
        refresh_db_rates(db)
    except Exception as e:
        logger.warning(f"Exchange rate refresh failed (non-critical): {e}")

    try:
        _check_wishlist_targets(db)
    except Exception as e:
        logger.warning(f"Wishlist target check failed (non-critical): {e}")

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

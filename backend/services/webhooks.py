import logging
import threading
from datetime import datetime, timezone

import httpx

import services.settings as settings_service

logger = logging.getLogger(__name__)

_TIMEOUT = 5.0


def _post(credential_id: int, target_url: str, event: str, data: dict, verify_tls: bool = True) -> None:
    def run():
        from database import SessionLocal
        db = SessionLocal()
        try:
            payload = {
                "event": event,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **data,
            }
            try:
                with httpx.Client(timeout=_TIMEOUT, verify=verify_tls) as client:
                    r = client.post(target_url, json=payload)
                logger.info(f"Home Assistant webhook '{event}' -> HTTP {r.status_code}")
            except Exception as exc:
                logger.info(f"Home Assistant webhook '{event}' failed (non-critical): {exc}")
                return

            try:
                import models
                cred = db.get(models.WebhookCredential, credential_id)
                if cred:
                    cred.last_used_at = datetime.now(timezone.utc)
                    db.commit()
            except Exception as exc:
                logger.info(f"Failed to update webhook last_used_at (non-critical): {exc}")
        finally:
            db.close()

    threading.Thread(target=run, daemon=True).start()


def _send_to_user(db, user, event: str, data: dict) -> None:
    if settings_service.get(db, "home_assistant_integration_enabled") != "true":
        return
    if user is None:
        return

    import models
    credentials = (
        db.query(models.WebhookCredential)
        .filter(
            models.WebhookCredential.user_id == user.id,
            models.WebhookCredential.enabled == True,  # noqa: E712
            models.WebhookCredential.target_url.isnot(None),
            models.WebhookCredential.target_url != "",
        )
        .all()
    )
    for cred in credentials:
        _post(cred.id, cred.target_url, event, data, verify_tls=cred.verify_tls)


def notify_trade_event(db, trade, event: str, initiator, counterpart) -> None:
    data = {
        "trade_id": trade.id,
        "initiator": initiator.username if initiator else "",
        "counterpart": counterpart.username if counterpart else "",
    }
    _send_to_user(db, initiator, f"trade_{event}", data)
    _send_to_user(db, counterpart, f"trade_{event}", data)


def notify_wishlist_target_met(db, entry, current_price: float, currency: str) -> None:
    card = entry.card
    data = {
        "card_name": card.name,
        "set_code": card.set_code,
        "set_name": card.set_name,
        "foil": entry.foil,
        "target_price": entry.target_price,
        "current_price": current_price,
        "currency": currency,
    }
    _send_to_user(db, entry.owner, "wishlist_target_met", data)


def notify_test_event(credential) -> None:
    if not credential.target_url:
        return
    _post(credential.id, credential.target_url, "test", {"label": credential.label},
          verify_tls=credential.verify_tls)

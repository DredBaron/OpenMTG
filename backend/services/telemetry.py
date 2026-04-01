import os
import uuid
import logging
import threading
import time
from datetime import datetime, timezone

import httpx

from database import SessionLocal
import services.settings as settings_service

logger = logging.getLogger(__name__)

_TELEMETRY_URL = os.environ.get(
    "TELEMETRY_URL",
    "https://openmtg-telemetry.openmtg-telemetry-api.workers.dev/v1/hb",
)
_VERSION = "1.4.1"

_HEARTBEAT_INTERVAL = 24 * 60 * 60

# Suppression check

def is_suppressed() -> bool:
    return os.environ.get("NOTEL", "").lower() in ("1", "true", "yes")

# Anonymous ID

def get_or_create_id(db) -> str:
    existing = settings_service.get(db, "telemetry_id")
    if existing:
        return existing
    new_id = str(uuid.uuid4())
    settings_service.set_value(db, "telemetry_id", new_id)
    return new_id


def delete_id(db) -> None:
    settings_service.delete_setting(db, "telemetry_id")

# Heartbeat

def send_heartbeat(telemetry_id: str) -> bool:
    try:
        payload = {
            "id":      telemetry_id,
            "ts":      datetime.now(timezone.utc).isoformat(),
            "version": _VERSION
        }
        with httpx.Client(timeout=5.0) as client:
            r = client.post(_TELEMETRY_URL, json=payload)
        logger.info(f"Telemetry heartbeat → HTTP {r.status_code}")
        return r.status_code in (200, 204)
    except Exception as exc:
        logger.info(f"Telemetry heartbeat failed (non-critical): {exc}")
        return False

# Background scheduler

def _run_scheduler() -> None:
    logger.info("Telemetry scheduler started")
    time.sleep(15)

    while True:
        try:
            if not is_suppressed():
                db = SessionLocal()
                try:
                    if settings_service.get(db, "telemetry_enabled") == "true":
                        telemetry_id = get_or_create_id(db)
                        send_heartbeat(telemetry_id)
                finally:
                    db.close()
        except Exception as exc:
            logger.error(f"Telemetry scheduler error: {exc}")

        time.sleep(_HEARTBEAT_INTERVAL)


def start_scheduler() -> None:
    if is_suppressed():
        logger.info("Telemetry suppressed via NOTEL - scheduler not started")
        return
    t = threading.Thread(target=_run_scheduler, daemon=True)
    t.start()
    logger.info("Telemetry scheduler thread launched")

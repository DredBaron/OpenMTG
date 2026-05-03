import os
import uuid
import logging
import threading
import time
from datetime import datetime, timezone
import json

import httpx

from database import SessionLocal
import services.settings as settings_service

logger = logging.getLogger(__name__)

_TELEMETRY_URL = os.environ.get(
    "TELEMETRY_URL",
    "https://openmtg-telemetry.openmtg-telemetry-api.workers.dev/v1/hb",
)
_VERSION = "1.5.0"

_HEARTBEAT_INTERVAL = 24 * 60 * 60
_MIN_HEARTBEAT_GAP  = 23 * 60 * 60
_UUID_MAX_AGE_DAYS  = 60

# Suppression check

def is_suppressed() -> bool:
    return os.environ.get("NOTEL", "").lower() in ("1", "true", "yes")

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _round_to_minute(dt: datetime) -> datetime:
    return dt.replace(second=0, microsecond=0)

# Anonymous ID

def get_or_create_id(db) -> str:
    existing_id  = settings_service.get(db, "telemetry_id")
    created_str  = settings_service.get(db, "telemetry_id_created")
 
    if existing_id and created_str:
        try:
            created = datetime.fromisoformat(created_str)
            age_days = (_now_utc() - created).days
            if age_days < _UUID_MAX_AGE_DAYS:
                return existing_id
            logger.info(
                f"Telemetry UUID is {age_days} days old — rotating (limit: {_UUID_MAX_AGE_DAYS}d)"
            )
        except ValueError:
            logger.warning("Telemetry: malformed telemetry_id_created — regenerating UUID")
 
    new_id      = str(uuid.uuid4())
    created_ts  = _round_to_minute(_now_utc()).isoformat()
    settings_service.set_value(db, "telemetry_id",         new_id)
    settings_service.set_value(db, "telemetry_id_created", created_ts)
    logger.info("Telemetry: new UUID issued")
    return new_id

def delete_id(db) -> None:
    settings_service.delete_setting(db, "telemetry_id")
    settings_service.delete_setting(db, "telemetry_id_created")

# Heartbeat

def send_heartbeat(db, telemetry_id: str) -> bool:
    ts = _round_to_minute(_now_utc())
    payload = {
        "id":      telemetry_id,
        "ts":      ts.isoformat(),
        "version": _VERSION,
    }
 
    success = False
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.post(_TELEMETRY_URL, json=payload)
        logger.info(f"Telemetry heartbeat → HTTP {r.status_code}")
        success = r.status_code in (200, 204)
    except Exception as exc:
        logger.info(f"Telemetry heartbeat failed (non-critical): {exc}")
 
    if success:
        settings_service.set_value(db, "telemetry_last_sent",   ts.isoformat())
        settings_service.set_value(db, "telemetry_last_packet", json.dumps(payload))
 
    return success

def _last_heartbeat_dt(db) -> datetime | None:
    raw = settings_service.get(db, "telemetry_last_sent")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None
 
def within_min_gap(db) -> bool:
    last = _last_heartbeat_dt(db)
    if last is None:
        return False
    elapsed = (_now_utc() - last).total_seconds()
    return elapsed < _MIN_HEARTBEAT_GAP

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
                        if within_min_gap(db):
                            logger.info(
                                "Telemetry: last heartbeat within 23 h — skipping this tick"
                            )
                        else:
                            telemetry_id = get_or_create_id(db)
                            send_heartbeat(db, telemetry_id)
                finally:
                    db.close()
        except Exception as exc:
            logger.error(f"Telemetry scheduler error: {exc}")
 
        interval = _HEARTBEAT_INTERVAL
        logger.debug(f"Telemetry: next heartbeat in {interval / 3600:.2f} h")
        time.sleep(interval)


def start_scheduler() -> None:
    if is_suppressed():
        logger.info("Telemetry suppressed via NOTEL - scheduler not started")
        return
    t = threading.Thread(target=_run_scheduler, daemon=True)
    t.start()
    logger.info("Telemetry scheduler thread launched")

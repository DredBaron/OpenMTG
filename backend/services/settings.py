from sqlalchemy.orm import Session
import models

DEFAULTS = {
    "price_refresh_hours": "72",
    "price_history_days": "90",
    "telemetry_enabled": "false",
    "telemetry_last_sent": "",
    "telemetry_last_packet": "",
    "telemetry_id_created": "",
    "showroom_enabled": "true",
    "card_search_enabled": "true",
    "trades_enabled": "true",
}

_cache: dict | None = None


def _load(db: Session) -> None:
    global _cache
    _cache = dict(DEFAULTS)
    rows = {row.key: row.value for row in db.query(models.Setting).all()}
    if "scanner_enabled" in rows and "card_search_enabled" not in rows:
        rows["card_search_enabled"] = rows.pop("scanner_enabled")
    _cache.update(rows)


def get(db: Session, key: str) -> str:
    if _cache is None:
        _load(db)
    return _cache.get(key, "")


def get_int(db: Session, key: str) -> int:
    val = get(db, key)
    return int(val) if val else 0


def set_value(db: Session, key: str, value: str):
    global _cache
    row = db.query(models.Setting).filter(models.Setting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(models.Setting(key=key, value=value))
    db.commit()
    if _cache is not None:
        _cache[key] = value


def delete_setting(db: Session, key: str) -> None:
    global _cache
    row = db.query(models.Setting).filter(models.Setting.key == key).first()
    if row:
        db.delete(row)
        db.commit()
    if _cache is not None:
        _cache.pop(key, None)


def get_all(db: Session) -> dict:
    if _cache is None:
        _load(db)
    return dict(_cache)

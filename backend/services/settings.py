from sqlalchemy.orm import Session
import models

DEFAULTS = {
    "price_refresh_hours": "72",   # 3 days
    "scryfall_rps":        "1",    # requests per second
}


def get(db: Session, key: str) -> str:
    row = db.query(models.Setting).filter(models.Setting.key == key).first()
    if row:
        return row.value
    return DEFAULTS.get(key, "")


def get_int(db: Session, key: str) -> int:
    return int(get(db, key))


def set_value(db: Session, key: str, value: str):
    row = db.query(models.Setting).filter(models.Setting.key == key).first()
    if row:
        row.value = value
    else:
        db.add(models.Setting(key=key, value=value))
    db.commit()


def get_all(db: Session) -> dict:
    rows = db.query(models.Setting).all()
    result = dict(DEFAULTS)
    for row in rows:
        result[row.key] = row.value
    return result

"""Server-side enforcement of the admin feature toggles.

Hiding a disabled feature in the UI is not enough: its API endpoints must refuse requests too.
Each gated router declares ``Depends(require_feature(<setting key>))`` at router level so every
endpoint it has (including ones added later) is covered. The public ``/status`` endpoints live on
separate, ungated routers so the frontend can always ask whether a feature is on.
"""
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import services.settings as settings_service

# Setting key -> name used in the 403 message.
FEATURES = {
    "showroom_enabled":                   "Showroom",
    "card_search_enabled":                "Card search",
    "trades_enabled":                     "Trades",
    "home_assistant_integration_enabled": "Home Assistant integration",
}


def is_enabled(db: Session, key: str) -> bool:
    """Whether a feature is on. Features that default to on stay on unless explicitly "false";
    features that default to off need an explicit "true"."""
    if key not in FEATURES:
        raise KeyError(f"Unknown feature toggle: {key}")
    value = settings_service.get(db, key)
    if settings_service.DEFAULTS.get(key) == "true":
        return value != "false"
    return value == "true"


def require_feature(key: str):
    """Router dependency that answers 403 while the feature is disabled."""
    if key not in FEATURES:
        raise KeyError(f"Unknown feature toggle: {key}")
    detail = f"{FEATURES[key]} is disabled on this server"

    def _require_enabled(db: Session = Depends(get_db)) -> None:
        if not is_enabled(db, key):
            raise HTTPException(status_code=403, detail=detail)

    return _require_enabled

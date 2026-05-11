import httpx
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FRANKFURTER_V1 = "https://api.frankfurter.dev/v1"
FRANKFURTER_V2 = "https://api.frankfurter.dev/v2"


def validate_and_fetch(code: str) -> float | None:
    """Check if a currency code is supported by Frankfurter and return its current USD rate.
    Returns None if the code is invalid or the request fails."""
    try:
        r = httpx.get(f"{FRANKFURTER_V2}/rate/USD/{code.upper()}", timeout=10)
        if r.status_code != 200:
            return None
        return float(r.json()["rate"])
    except Exception as e:
        logger.warning(f"Frankfurter validation failed for {code}: {e}")
        return None


def refresh_db_rates(db: Session) -> None:
    """Batch-update stored exchange rates for all DB-managed converted currencies."""
    from models import ConvertedCurrency
    currencies = db.query(ConvertedCurrency).all()
    if not currencies:
        return
    codes = [c.code for c in currencies]
    try:
        r = httpx.get(
            f"{FRANKFURTER_V1}/latest",
            params={"base": "USD", "symbols": ",".join(codes)},
            timeout=10,
        )
        r.raise_for_status()
        rates = r.json().get("rates", {})
        now = datetime.now(timezone.utc)
        for c in currencies:
            if c.code in rates:
                c.rate = float(rates[c.code])
                c.rate_updated_at = now
        db.commit()
        logger.info(f"Exchange rates updated: {sorted(rates.keys())}")
    except Exception as e:
        logger.warning(f"Exchange rate refresh failed: {e}")

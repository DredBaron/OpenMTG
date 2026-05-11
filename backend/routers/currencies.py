from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from markets import MARKETS

router = APIRouter(tags=["currencies"])


@router.get("/currencies")
def list_currencies(db: Session = Depends(get_db)):
    result = {}

    for code, m in MARKETS.items():
        result[code] = {
            "symbol":           m["symbol"],
            "display":          m["display"],
            "supports_history": m["supports_history"],
            "convert_from":     None,
            "rate":             None,
        }

    for c in db.query(models.ConvertedCurrency).order_by(models.ConvertedCurrency.code).all():
        result[c.code.lower()] = {
            "symbol":           c.symbol,
            "display":          c.code,
            "supports_history": False,
            "convert_from":     "usd",
            "rate":             c.rate,
        }

    return result

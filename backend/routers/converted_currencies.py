from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from database import get_db
from security import get_current_user
import models
import schemas
from markets import MARKETS
from services import exchange_rates

router = APIRouter(prefix="/admin/currencies", tags=["admin"])


def _require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("", response_model=list[schemas.ConvertedCurrencyOut])
def list_converted_currencies(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_admin),
):
    return db.query(models.ConvertedCurrency).order_by(models.ConvertedCurrency.code).all()


@router.post("", response_model=schemas.ConvertedCurrencyOut, status_code=201)
def add_converted_currency(
    payload: schemas.AddCurrencyRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_admin),
):
    code = payload.code.upper()

    if code.lower() in MARKETS:
        raise HTTPException(status_code=400, detail=f"{code} is already supported natively")

    if db.query(models.ConvertedCurrency).filter_by(code=code).first():
        raise HTTPException(status_code=409, detail=f"{code} is already configured")

    rate = exchange_rates.validate_and_fetch(code)
    if rate is None:
        raise HTTPException(
            status_code=422,
            detail=f"Currency {code} is not supported by Frankfurter"
        )

    entry = models.ConvertedCurrency(
        code=code,
        symbol=payload.symbol,
        rate=rate,
        rate_updated_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/{code}", response_model=schemas.ConvertedCurrencyOut)
def update_converted_currency(
    code: str,
    payload: schemas.UpdateCurrencyRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_admin),
):
    entry = db.query(models.ConvertedCurrency).filter_by(code=code.upper()).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Currency not found")
    entry.symbol = payload.symbol
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{code}", status_code=204)
def remove_converted_currency(
    code: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_require_admin),
):
    entry = db.query(models.ConvertedCurrency).filter_by(code=code.upper()).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Currency not found")
    db.delete(entry)
    db.commit()

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import get_db
import models
import schemas
from security import hash_password, verify_password, create_access_token, get_current_user
from limiter import limiter
from markets import MARKETS
import login_throttle

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/setup-required")
def setup_required(db: Session = Depends(get_db)):
    count = db.query(models.User).count()
    return {"setup_required": count == 0}


@router.post("/setup", response_model=schemas.UserOut, status_code=201)
@limiter.limit("5/hour")
def setup_admin(request: Request, payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).count() > 0:
        raise HTTPException(
            status_code=403,
            detail="Setup already complete. An admin must create new accounts."
        )
    user = models.User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_admin=True,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Setup already complete. An admin must create new accounts."
        )
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.LoginResponse)
@limiter.limit("20/minute")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    _AUTH_FAILURE = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password"
    )

    if login_throttle.is_locked(form.username):
        raise _AUTH_FAILURE

    user = db.query(models.User).filter(models.User.username == form.username).first()
    if not user or not user.is_active or not verify_password(form.password, user.hashed_password):
        login_throttle.record_failure(form.username)
        raise _AUTH_FAILURE

    login_throttle.clear(form.username)
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.patch("/me/currency", response_model=schemas.UserOut)
def set_currency(
    payload: schemas.CurrencyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    code = payload.preferred_currency.lower()
    if code not in MARKETS:
        exists = db.query(models.ConvertedCurrency).filter_by(code=code.upper()).first()
        if not exists:
            raise HTTPException(status_code=422, detail=f"Unsupported currency: {code}")
    current_user.preferred_currency = code
    db.commit()
    db.refresh(current_user)
    return current_user
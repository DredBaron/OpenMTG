from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from security import hash_password, verify_password, create_access_token, get_current_user
from limiter import limiter

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
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.LoginResponse)
@limiter.limit("20/minute")
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
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
    current_user.preferred_currency = payload.preferred_currency
    db.commit()
    db.refresh(current_user)
    return current_user
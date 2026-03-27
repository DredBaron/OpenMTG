from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from security import hash_password, get_current_user
import models
import schemas
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    password: str | None = None


@router.get("/users", response_model=list[schemas.UserOut], dependencies=[Depends(require_admin)])
def list_users(
    db: Session = Depends(get_db),
):
    return db.query(models.User).order_by(models.User.created_at).all()


@router.post("/users", response_model=schemas.UserOut, status_code=201, dependencies=[Depends(require_admin)])
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
):
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        is_admin=payload.is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    payload: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Prevent admin from deactivating or demoting themselves
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot modify your own account here")

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.password:
        user.hashed_password = hash_password(payload.password)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(require_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    db.delete(user)
    db.commit()

from datetime import datetime, timedelta, timezone
from functools import cache
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
import jwt_secret
import models

SECRET_KEY = jwt_secret.load()

ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


@cache
def dummy_password_hash() -> str:
    """A real bcrypt hash (same cost as hash_password) to check against when the
    username does not exist, so the login takes as long as it does for a real user."""
    return hash_password("openmtg-dummy-password")


def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_user_token(user: models.User) -> str:
    """Issue a login token bound to the user's current token_version."""
    return create_access_token({"sub": user.username, "ver": user.token_version})


def revoke_user_tokens(user: models.User) -> None:
    """Invalidate every token already issued to this user (call before committing)."""
    user.token_version = (user.token_version or 0) + 1


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_version = payload.get("ver")
        # Tokens issued before token versions existed carry no "ver" claim and are rejected.
        if username is None or type(token_version) is not int:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None or not user.is_active or user.token_version != token_version:
        raise credentials_exception
    return user

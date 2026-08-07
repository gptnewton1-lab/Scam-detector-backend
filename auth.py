"""
Authentication & security helpers.

- Passwords are hashed with bcrypt (no fragile passlib dependency).
- API tokens are signed JWTs with an expiry.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from config import get_settings
from database import engine
from models import User

settings = get_settings()

# Tells FastAPI where the token-based login endpoint is for Swagger's Authorize
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plain password matches the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        # Malformed / non-bcrypt hash -> treat as not matching.
        return False


def get_password_hash(password: str) -> str:
    """Hash a password for storage, honoring the configured cost factor."""
    # bcrypt only uses the first 72 bytes, so truncate explicitly.
    return bcrypt.hashpw(
        password.encode("utf-8")[:72],
        bcrypt.gensalt(rounds=settings.bcrypt_rounds),
    ).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT that expires after a short time."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Return the User if credentials are valid, else None."""
    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Decode the JWT and load the matching user; raise 401 if invalid."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    with Session(engine) as session:
        user = session.exec(
            select(User).where(User.username == username)
        ).first()
        if user is None:
            raise credentials_exception
        return user


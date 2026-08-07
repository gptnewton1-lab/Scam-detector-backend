from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    # Corrected: datetime.utcnow() is deprecated; use timezone-aware UTC now.
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=_utcnow)


class ScanResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    text: str
    score: int
    label: str
    reasons: str
    created_at: datetime = Field(default_factory=_utcnow)

#used for incoming data when creating new scan
class ScanResultCreate(SQLModel):
    text: str = Field(min_length=1, max_length=5000)


#used for signup input
class UserCreate(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


#safe user output shape
class UserRead(SQLModel):
    id: int
    username: str
    email: str


#used to shape token output
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


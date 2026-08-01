from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScanResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    text: str
    score: int
    label: str
    reasons: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

#used for incoming data when creating new scan
class ScanResultCreate(SQLModel):
    text: str

#used  for signup input
class UserCreate(SQLModel):
    username: str
    email: str
    password: str

#safe user output shape
class UserRead(SQLModel):
    id: int
    username: str
    email: str

#used to shape token output
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

#usedto shape token data
class TokenData(SQLModel):
    username: Optional[str] = None

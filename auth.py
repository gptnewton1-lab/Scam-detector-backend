import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlmodel import Session, select

from database import engine
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# This tells FastAPI where the login endpoint is for token auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
# Use a secret key from the environment, with a fallback for local testing
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

#checks a plain password against a stored hash
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

#hashes a password for storage
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

#creates a jwt token with an expiring time 
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    # Create a JWT token that expires after a short time
    to_encode = data.copy()
    if expires_delta:
        # CORRECTED: Changed datetime.utcnow() to datetime.now(timezone.utc) to remove deprecation warning
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # CORRECTED: Changed datetime.utcnow() to datetime.now(timezone.utc) to remove deprecation warning
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

#verifies username and password against the database and returns the user if valid
def authenticate_user(username: str, password: str) -> Optional[User]:
    # Check whether the username exists and the password matches the stored hash
    with Session(engine) as session:
        # CORRECTED: Replaced legacy .query().filter() syntax with standard session.exec(select()) SQLModel structure
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

#decodes the jwt token and gets the current user from database, raises exceptions if the token is invalid or user is not found 
def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Decode the token and return the logged-in user if the token is valid
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    with Session(engine) as session:
        # CORRECTED: Replaced legacy .query().filter() syntax with standard session.exec(select()) SQLModel structure
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            raise credentials_exception
        return user

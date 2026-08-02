from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from database import create_db_and_tables, get_session
from models import ScanResult, Token, User, UserCreate, UserRead
from scam_logic import analyze_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)


class MessageInput(BaseModel):
    text: str


class LoginInput(BaseModel):
    username: str
    password: str


@app.get("/")
def home():
    return {"message": "Welcome to the Scam Detector API"}


@app.get("/health")
# Simple endpoint to check that the backend is running
def health():
    return {"status": "ok", "service": "scam-detector-backend"}


@app.get("/analyze")
def analyze_info():
    return {
        "message": "Use a POST request to this endpoint with JSON like {'text': 'hello'}"
    }


@app.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
# Create a new user account and save it in the database
def register(user_data: UserCreate, session: Session = Depends(get_session)):
    existing_user = session.exec(
        select(User).where(
            (User.username == user_data.username) | (User.email == user_data.email)
        )
    ).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.post("/login", response_model=Token)
# Verify username/password and return a token for protected routes
def login(payload: LoginInput):
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/analyze")
# Analyze the message, save the result, and link it to the logged-in user
def analyze(
    data: MessageInput,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    score, label, reasons = analyze_text(data.text)

    scan_result = ScanResult(
        user_id=current_user.id,
        text=data.text,
        score=score,
        label=label,
        reasons=" | ".join(reasons),
    )
    session.add(scan_result)
    session.commit()
    session.refresh(scan_result)

    return {
        "received_text": data.text,
        "length": len(data.text),
        "score": score,
        "reasons": reasons,
        "label": label,
        "status": "ok",
        "saved_to_history": True,
        "history_id": scan_result.id,
        "user": current_user.username,
    }


@app.get("/history")
# Return all previous scam checks saved for the logged-in user
def history(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    results = session.exec(select(ScanResult).where(ScanResult.user_id == current_user.id)).all()
    return [
        {
            "id": result.id,
            "text": result.text,
            "score": result.score,
            "label": result.label,
            "reasons": result.reasons,
            "created_at": result.created_at,
        }
        for result in results
    ]


@app.get("/me")
# Return basic info about the currently logged-in user
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}

"""
Scam Detector API - production-grade JSON backend for the Lovable frontend.

Only exposes the JSON API that the React/Lovable client needs. There is no
server-rendered UI here; the frontend is a separate project.
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
)
from config import get_settings
from database import create_db_and_tables, get_session
from models import ScanResult, Token, User, UserCreate, UserRead
from ratelimit import RateLimiter
from scam_logic import analyze_text

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate config and create tables on startup.
    settings.validate()
    create_db_and_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Only allow our configured hostnames (blocks Host-header attacks).
app.add_middleware(
    TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list
)

# Allow the Lovable frontend origin(s) to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Request/response models
# --------------------------------------------------------------------------
class MessageInput(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


# --------------------------------------------------------------------------
# Rate limiters (per-client, in-memory)
# --------------------------------------------------------------------------
auth_limiter = RateLimiter(
    settings.rate_limit_requests, settings.rate_limit_window_seconds
)
public_limiter = RateLimiter(
    settings.public_analyze_rate_limit, settings.rate_limit_window_seconds
)


# --------------------------------------------------------------------------
# Health check (for load balancers / uptime monitors)
# --------------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


# --------------------------------------------------------------------------
# Root info
# --------------------------------------------------------------------------
@app.get("/")
def root() -> dict:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "message": "Use the /docs page or the /api/* JSON endpoints.",
    }

# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
@app.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    auth_limiter.check(auth_limiter.client_key(request))

    existing = session.exec(
        select(User).where(
            (User.username == user_data.username) | (User.email == user_data.email)
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=400, detail="Username or email already exists"
        )

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
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Form-based login for Swagger's Authorize popup."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/api/login", response_model=Token)
def login_json(data: LoginRequest, request: Request):
    """JSON login for the Lovable SPA."""
    auth_limiter.check(auth_limiter.client_key(request))

    user = authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    }


# --------------------------------------------------------------------------
# Scanning
# --------------------------------------------------------------------------
@app.post("/analyze")
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
def history(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    results = session.exec(
        select(ScanResult).where(ScanResult.user_id == current_user.id)
    ).all()
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


@app.post("/analyze-public")
def analyze_public(data: MessageInput, request: Request):
    """Rate-limited, unauthenticated scan for quick testing."""
    public_limiter.check(public_limiter.client_key(request))
    score, label, reasons = analyze_text(data.text)
    return {
        "received_text": data.text,
        "length": len(data.text),
        "score": score,
        "reasons": reasons,
        "label": label,
        "status": "ok",
    }


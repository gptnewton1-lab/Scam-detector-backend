# this is the app
from contextlib import asynccontextmanager  # Added for database initialization
from fastapi import FastAPI, Depends        # Added Depends for future DB usage
from pydantic import BaseModel
from sqlmodel import Session                # Added for database sessions

from database import create_db_and_tables, get_session  # Added database hooks
from scam_logic import analyze_text

# Automatically create your database.db file and tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)  # Tied lifespan hook to the FastAPI app

# post route
class MessageInput(BaseModel):
    text: str

# this is the home route
@app.get("/")
def home():
    return {"message": "Welcome to the Scam Detector API"}


@app.get("/analyze")
def analyze_info():
    return {
        "message": "Use a POST request to this endpoint with JSON like {'text': 'hello'}"
    }


@app.post("/analyze")
def analyze(data: MessageInput):
    score, label, reasons = analyze_text(data.text)

    return {
        "received_text": data.text,
        "length": len(data.text),
        "score": score,
        "reasons": reasons,
        "label": label,
        "status": "ok"
    }

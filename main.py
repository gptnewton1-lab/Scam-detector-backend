import jwt
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status, Form, Response, Request
from fastapi.responses import HTMLResponse, RedirectResponse
# CORRECTED: Imported OAuth2PasswordRequestForm to make Swagger UI form submissions work natively
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates  # CORRECTED: Added for silky Python UI HTML rendering
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, select

from auth import authenticate_user, create_access_token, get_current_user, get_password_hash, SECRET_KEY, ALGORITHM
from database import create_db_and_tables, get_session, engine
from models import ScanResult, Token, User, UserCreate, UserRead
from scam_logic import analyze_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

# CORRECTED: Mount the HTML templates directory to serve Python views
templates = Jinja2Templates(directory="templates")
# Serve static assets (JS/CSS/images) from ./static
app.mount("/static", StaticFiles(directory="static"), name="static")


# CORRECTED: Helper utility to verify browser cookie identities for pure Python UI page updates
def get_ui_user(request: Request) -> str | None:
    token = request.cookies.get("ui_session")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


class MessageInput(BaseModel):
    text: str


# NOTE: Keeping this class here for reference, but Swagger UI requires Form Data instead of JSON for the main OAuth2 popup.
class LoginInput(BaseModel):
    username: str
    password: str


# ==========================================
# 🆕 NEW SECTION: PYTHON JINJA2 FRONTEND RENDERING ROUTES
# ==========================================

@app.get("/", response_class=HTMLResponse)
def show_dashboard(request: Request, result: dict = None, text_scanned: str = None):
    """Redirect root to the working simple UI for quick frontend-backend testing."""
    return RedirectResponse(url="/simple-ui", status_code=status.HTTP_302_FOUND)


@app.post("/register-ui")
def ui_register(username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    """Handles new user signups from the silky UI form input elements."""
    with Session(engine) as session:
        dup = session.exec(select(User).where((User.username == username) | (User.email == email))).first()
        if dup:
            return RedirectResponse(url="/?error=exists", status_code=status.HTTP_303_SEE_OTHER)
        
        user = User(username=username, email=email, hashed_password=get_password_hash(password))
        session.add(user)
        session.commit()
    
    # Secure auto-login transition immediately after registration
    token = create_access_token({"sub": username})
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="ui_session", value=token, httponly=True)
    return response


@app.post("/login-ui")
def ui_login(username: str = Form(...), password: str = Form(...)):
    """Validates login forms from the web view and provisions browser cookie credentials."""
    user = authenticate_user(username, password)
    if not user:
        return RedirectResponse(url="/?error=auth", status_code=status.HTTP_303_SEE_OTHER)
    
    token = create_access_token({"sub": username})
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="ui_session", value=token, httponly=True)
    return response


@app.get("/logout-ui")
def ui_logout():
    """Wipes the browser session cookie token to process secure logouts safely."""
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="ui_session")
    return response


@app.post("/analyze-ui")
def ui_analyze(request: Request, text: str = Form(...)):
    """Processes UI text inputs, calls scam logic filters, and commits results to SQLite history."""
    username = get_ui_user(request)
    if not username:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
    score, label, reasons = analyze_text(text)
    
    with Session(engine) as session:
        user_rec = session.exec(select(User).where(User.username == username)).first()
        if user_rec:
            scan_record = ScanResult(
                user_id=user_rec.id,
                text=text,
                score=score,
                label=label,
                reasons=" | ".join(reasons)
            )
            session.add(scan_record)
            session.commit()
            
    analysis_data = {"score": score, "label": label, "reasons": reasons}
    return show_dashboard(request, result=analysis_data, text_scanned=text)


# ==========================================
# 🔌 STANDARD PURE JSON BACKEND API ROUTES
# ==========================================

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
# CORRECTED: Changed 'payload: LoginInput' to 'form_data: OAuth2PasswordRequestForm = Depends()' so it hooks perfectly into Swagger's Authorize popups
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # CORRECTED: Swapped 'payload.username' and 'payload.password' for 'form_data.username' and 'form_data.password'
    user = authenticate_user(form_data.username, form_data.password)
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


# Minimal public analyze endpoint (no auth) for quick frontend testing
@app.post("/analyze-public")
def analyze_public(data: MessageInput):
        score, label, reasons = analyze_text(data.text)
        return {
                "received_text": data.text,
                "length": len(data.text),
                "score": score,
                "reasons": reasons,
                "label": label,
                "status": "ok",
        }


# Simple single-file UI to test frontend -> backend interaction without Jinja
@app.get("/simple-ui", response_class=HTMLResponse)
def simple_ui():
        html = """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset='utf-8'/>
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Scam Detector - Simple JS UI</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-50 text-gray-800">
            <div class="max-w-4xl mx-auto py-12 px-4">
                <header class="flex items-center justify-between mb-8">
                    <h1 class="text-2xl font-bold">Scam Detector</h1>
                    <div class="space-x-2">
                        <button id="btn-logout" class="hidden bg-red-500 text-white px-3 py-1 rounded">Logout</button>
                    </div>
                </header>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <section class="p-6 bg-white rounded shadow">
                        <h2 class="text-lg font-semibold mb-4">Public Analyze (no login)</h2>
                        <textarea id="pub-text" class="w-full border rounded p-2" rows="6">Urgent! Send money now to claim your prize.</textarea>
                        <div class="mt-3 flex gap-2">
                            <button id="pub-analyze" class="bg-blue-600 text-white px-4 py-2 rounded">Analyze</button>
                            <button id="pub-clear" class="bg-gray-200 px-3 py-2 rounded">Clear</button>
                        </div>
                        <pre id="pub-out" class="mt-4 bg-gray-100 p-3 rounded text-sm overflow-auto"></pre>
                    </section>

                    <section class="p-6 bg-white rounded shadow">
                        <h2 class="text-lg font-semibold mb-4">Authenticated Analyze</h2>
                        <div id="auth-ui">
                            <div class="mb-3">
                                <input id="username" placeholder="username" class="w-full border rounded p-2 mb-2" />
                                <input id="password" placeholder="password" type="password" class="w-full border rounded p-2" />
                            </div>
                            <div class="flex gap-2 mb-4">
                                <button id="btn-login" class="bg-green-600 text-white px-4 py-2 rounded">Login</button>
                                <button id="btn-register" class="bg-yellow-500 text-white px-4 py-2 rounded">Register</button>
                            </div>
                            <textarea id="auth-text" class="w-full border rounded p-2" rows="4">You have won a prize! Click here to claim.</textarea>
                            <div class="mt-3">
                                <button id="auth-analyze" class="bg-indigo-600 text-white px-4 py-2 rounded">Analyze as User</button>
                            </div>
                            <pre id="auth-out" class="mt-4 bg-gray-100 p-3 rounded text-sm overflow-auto"></pre>
                        </div>
                    </section>
                </div>

                <footer class="mt-8 text-sm text-gray-600">Built with plain JS and Tailwind — calls <code>/analyze-public</code> and <code>/login</code>/<code>/analyze</code>.</footer>
            </div>

                <script src="/static/app.js"></script>
        </body>
        </html>
        """
        return HTMLResponse(content=html)

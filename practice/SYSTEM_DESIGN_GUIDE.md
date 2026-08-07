# Backend Engineering & System Design — Your FastAPI Crash Course

A beginner-friendly guide built around **your** Scam Detector project. The goal is to
teach you the *logic and structure* a backend engineer thinks in — not just syntax.

---

## Part 0 — The ONE mental model everything hangs on

A backend engineer answers one question over and over:

> **"A client made a request. How does my server produce a correct, fast,
> secure response — and remember what it needs to remember?"**

Everything below is just structure around that question. When you get lost,
come back to this sentence.

The flow is always the same shape:

```
Client (mobile/web)
   │  1. sends an HTTP request (method + path + body + headers)
   ▼
[ Middleware ]  ← runs before/after the route (CORS, rate-limit, TrustedHost)
   ▼
[ Route/Controller ]  ← reads the request, validates inputs
   ▼
[ Business Logic ]  ← makes decisions (your scam scoring)
   ▼
[ Data layer ]  ← talks to the database (save/load)
   ▼
Client gets an HTTP response (status code + JSON body)
```

Understanding **this flow** is worth more than memorizing any framework syntax.

---

## Part 1 — The request lifecycle, using YOUR code

When the Lovable frontend calls `POST /analyze` with `{"text": "Urgent! Send money now!"}`:

1. **Middleware** runs first. `CORSMiddleware` checks the caller's origin is allowed;
   `TrustedHostMiddleware` checks the Host header is allowed.
2. FastAPI matches `POST /analyze` to the `analyze()` function.
3. FastAPI **validates the body** against `MessageInput` (text must be 1–5000 chars).
   If it fails → automatic `422`, your function never runs.
4. **Dependency injection** gives the function what it needs:
   - `current_user` from `Depends(get_current_user)` → decodes the JWT → the logged-in user.
   - `session` from `Depends(get_session)` → a database session.
5. The function calls `analyze_text(...)` (business logic) → gets `score, label, reasons`.
6. It saves a `ScanResult` row (data layer).
7. It returns a dict → FastAPI turns it into JSON → sends back with status 200.

**Key insight:** FastAPI does the boring plumbing (validation, request parsing, JSON
serialization, status codes). Your job is just to write the decision logic.

---

## Part 2 — Layered architecture (your project)

"Layered architecture" = each concern lives in its own file. Why? **So you can change
one thing without breaking everything else.**

| Layer | File | Job | Example |
|---|---|---|---|
| API / routing | `main.py` | HTTP in/out | endpoints, status codes, middleware |
| Security | `auth.py` | who can do what | hashing, JWT |
| Business | `scam_logic.py` | the real decisions | scoring text |
| Data access | `database.py` | DB connection | engine, sessions |
| Schema | `models.py` | shapes of data | `User`, `ScanResult` |
| Config | `config.py` | environment settings | secret, DB url |

**Interview point you can say:** *"I separated routing from business logic from data
access so the app is testable and each piece has one responsibility."*

**Concrete win:** because DB logic lives behind `database.py` + `models.py`, switching
from SQLite to Postgres is a config change (`DATABASE_URL`), not a code rewrite. That's
**abstraction** — hiding details behind a stable interface.

---

## Part 3 — FastAPI syntax, explained (not memorized)

### Decorators = "handle this type of request"
```python
@app.post("/analyze")        # 'when someone POSTs to /analyze...'
def analyze(...):            # '...call this function'
```

### Pydantic models = "describe the data, get validation free"
```python
class MessageInput(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
```
You wrote a *schema*, and FastAPI/Pydantic enforce it for you. That's **validation as a
feature** — you don't hand-write `if len(text) > 5000`.

### Dependency Injection = "declare what I need; framework provides it"
```python
def analyze(data: MessageInput, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
```
`Depends(...)` means: "run this helper, pass me its result." FastAPI builds the dependency
tree, runs it, and injects the results. Benefits: **reusable, testable** auth/session logic.

### Status codes = "the shortcut for what happened"
- `200` OK · `201` Created · `400` bad request · `401` not authenticated · `403` forbidden
- `404` not found · `422` invalid input · `429` too many requests · `500` server error

A good API tells the client *why* with the right code — that's part of **API design**.

---

## Part 4 — Authentication, the part everyone asks about

Two big ideas: **how passwords are stored** and **how identity is proven**.

### (a) Passwords: never store plaintext
You store a **hash** (`bcrypt`). It's one-way — you cannot get the password back from it.
At login you rehash the incoming password and compare. Even if the DB leaks, passwords
don't. Cost factor (`rounds`) makes brute-forcing slower.

```python
get_password_hash(password)      # store this
verify_password(password, hash)  # True/False at login
```

### (b) Proving identity: "stateless" tokens (JWT)
After login you hand the client a **JWT**: `header.payload.signature`.

- `payload` says *who* (`"sub": username`) and *when it expires* (`exp`).
- `signature` is a **cryptographic hash** of header+payload+`SECRET_KEY`.

The magic: the server doesn't store sessions. It just re-verifies the signature on every
request with `SECRET_KEY`. If the token was tampered with, the signature won't match →
`401`. This is "stateless auth."

```python
# create (at login):
jwt.encode(payload, SECRET_KEY, algorithm="HS256")
# verify (on each protected request):
jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

**Interview gold:** know the difference between **sessions** (stateful — server stores
them, can revoke instantly) vs **JWT** (stateless — easy to scale, but can't be trivially
revoked before expiry). Be ready to say when each fits.

---

## Part 5 — Databases & ORMs

ORM = **Object-Relational Mapping** = you write Python classes; it writes SQL for you.

```python
class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    username: str = Field(unique=True)
```
`SQLModel`/SQLAlchemy turns that into a table, gives you `select(...)` queries, and
manages **transactions** (commit = save, rollback = undo).

Relationships are how data connects:
```python
class ScanResult(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id")   # "this scan belongs to a user"
```
That `foreign_key` links `ScanResult` → `User` (one user → many scans).

**Key concepts:** index (fast lookups), unique (no duplicates), foreign key (integrity),
transaction (all-or-nothing updates). Knowing these four covers a lot of interviews.

---

## Part 6 — Security & operations (what makes it "production")

- **CORS** — browsers block cross-origin calls unless the server opts in. You whitelist
  origins. (Dev vs real domain matter.)
- **Input validation** — never trust the client; enforce bounds (422).
- **Rate limiting** — someone shouldn't brute-force logins for free. Throttle by IP (429).
- **Secrets** — keys in env vars, not code. Fail fast if missing.
- **Health check** — `/health` so orchestrators/uptime monitors know it's alive.
- **TrustedHost** — reject requests with spoofed Host headers.

These are "ops + security hygiene" — the things that separate a demo from shipped software.
Name them in interviews.

---

## Part 7 — From project to micro-SaaS

The architecture you have is the foundation. Growth path:

1. **Bill** → Stripe (subscription).
2. **Gate** → add `plan` to `User`; a dependency checks it on `/analyze`.
3. **Quota** → count `ScanResult` rows per user/month.
4. **Scale** → SQLite→Postgres; in-memory rate limiter→Redis; multiple workers behind a
   load balancer (that's why you have `/health`).
5. **Observe** → logs + error tracking (e.g. Sentry).

The reason you built layering/abstraction *now* is so #1–5 don't require rewrites.

---

## Part 8 — How to talk about this in an interview (30-second pitch)

> "I built a scam-detection API for a React frontend. It's a layered FastAPI app:
> routes handle HTTP, a business-logic module does the scoring, and SQLModel handles a
> database behind a config layer. Auth is bcrypt hashing plus stateless JWTs, and I
> hardened it with CORS, input validation, rate limiting, and fail-fast config
> validation. The DB layer is abstracted so I can swap SQLite for Postgres by changing
> one config value. Next I'd add Stripe billing, usage quotas, and Redis rate limiting
> as it scales."

That paragraph demonstrates: architecture, security, data, and product thinking.


# Scam Detector API

A production-grade, JSON-only REST API backend for a scam/phishing message detector.
It powers a separate frontend (built with Lovable / React) and is structured so it can grow
into a paid micro-SaaS (plans, quotas, Stripe).

- **Framework:** FastAPI (Python 3.13)
- **Data:** SQLModel (SQLAlchemy) + SQLite for dev, Postgres-ready for prod
- **Auth:** bcrypt password hashing + stateless JWT bearer tokens
- **No UI in this repo** — it's a pure API. The frontend lives in its own project.

---

## Quick start

```bash
# 1. Install dependencies
python -m pip install -r requirements.txt

# 2. Make sure SECRET_KEY is set (see .env.example, then create .env)
# 3. Run the server
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

- Interactive API docs: <http://127.0.0.1:8000/docs>
- Health check:        <http://127.0.0.1:8000/health>

> Use the **system Python**, not the `.venv` (the venv is missing dependencies).
> If port 8000 is busy, free it first:
> ```powershell
> Get-NetTCPConnection -LocalPort 8000 -State Listen |
>   ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
> ```

---

## Project layout (layered architecture)

```
main.py        = API layer — routes, request/response validation, middleware
auth.py        = Security layer — bcrypt hashing + JWT issue/verify
scam_logic.py  = Business logic — the actual scam-scoring engine
database.py    = Data layer — engine creation + SQLite PRAGMAs
models.py      = Schema — SQLModel tables (User, ScanResult) + API shapes
config.py      = Settings — everything loaded from env vars / .env
ratelimit.py   = Infrastructure — in-memory per-IP rate limiter
```

Separation of concerns means each file has one job, which makes the app easy to
test, extend, and swap pieces (e.g. SQLite → Postgres is a config change, not a rewrite).

---

## Environment variables (`config.py`, sample in `.env.example`)

| Variable | Purpose | Dev default |
|---|---|---|
| `SECRET_KEY` | Signs JWTs. **Required.** Server refuses to start if missing/insecure. | set in `.env` |
| `DATABASE_URL` | Connection string | `sqlite:///./database.db` |
| `CORS_ORIGINS` | Allowed browser origins (your Lovable URL) | localhost:5173 |
| `ALLOWED_HOSTS` | Allowed Host headers (blocks host-header attacks) | localhost/127.0.0.1 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime | 30 |
| `BCRYPT_ROUNDS` | Password hash cost factor | 12 |
| `RATE_LIMIT_*` | Auth/public endpoint throttling | 20/60s, 10/60s |

`.env` is git-ignored; commit only `.env.example`.

---

## API reference

### Authentication flow
1. `POST /register` — create a user → `201`
2. `POST /api/login` — JSON login → returns `access_token`
3. Send the token on protected calls as `Authorization: Bearer <token>`

### Endpoints

| Method | Path | Auth | Body | Returns |
|---|---|---|---|---|
| GET | `/health` | – | – | service status |
| GET | `/` | – | – | API info |
| POST | `/register` | – | `{username, email, password}` | user (`201`) |
| POST | `/login` | – | form-encoded (Swagger OAuth) | `{access_token, token_type}` |
| POST | `/api/login` | – | JSON `{username, password}` | `{access_token, token_type}` |
| GET | `/me` | 🔒 | – | profile |
| POST | `/analyze` | 🔒 | `{text}` | scam score + reasons (saved to history) |
| GET | `/history` | 🔒 | – | user's past scans |
| POST | `/analyze-public` | – (rate-limited) | `{text}` | scam score (not saved) |

🔒 = requires `Authorization: Bearer <token>`

### Example: login + analyze (Lovable/React style)

```js
// 1. login
const res = await fetch("http://127.0.0.1:8000/api/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ username: "you", password: "strongpass123" }),
});
const { access_token } = await res.json();

// 2. analyze
const scan = await fetch("http://127.0.0.1:8000/analyze", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${access_token}`,
  },
  body: JSON.stringify({ text: "Urgent! Send money now to claim your prize." }),
});
const result = await scan.json();
```

---

## Security features (intentional)

- **bcrypt password hashing** — direct library (no fragile `passlib`), configurable cost.
- **JWT auth** — stateless, signed with `SECRET_KEY`, short expiry.
- **Secrets via env** — no hardcoded keys; fail-fast validation on boot.
- **CORS** — explicit allowed origins (not `*`).
- **TrustedHost middleware** — blocks Host-header attacks.
- **Input validation** — Pydantic min/max bounds → automatic `422`.
- **Rate limiting** — per-IP throttle on register/login/public analyze → `429`.

---

## Verified test results (full suite)

| Check | Result |
|---|---|
| register / duplicate / weak input | 201 / 400 / 422 ✅ |
| JSON login / wrong password | 200 + token / 401 ✅ |
| `/me`, `/analyze`, `/history` (authed) | 200 ✅ |
| `/analyze` without token | 401 ✅ |
| `/analyze-public` | 200 ✅ |
| rate limit | 429 ✅ |

Run your own end-to-end suite anytime against the live server.

---

## Deployment & micro-SaaS roadmap

1. **Deploy:** host on Render/Railway/Fly.io, point `DATABASE_URL` at Postgres,
   set `CORS_ORIGINS`/`ALLOWED_HOSTS` to your live Lovable domain, set a real `SECRET_KEY`.
2. **Payments:** add Stripe checkout.
3. **Plans/quota:** add a `plan` to `User` and a dependency that checks access on `/analyze`;
   count rows in `ScanResult` for monthly usage.
4. **Scale:** swap the in-memory rate limiter for Redis once running multiple workers/servers.
5. **Observability:** structured logging + error tracking (e.g. Sentry).

# Backend Interview Cheat Sheet

A one-page reference. Say these OUT LOUD — the goal is to sound natural, not robotic.

---

## The Master Mental Model
> "A client made a request. How does my server produce a correct, fast, secure response — and remember what it needs to remember?"

**Request pipeline (the same in almost every backend):**
```
Middleware → Auth → Validate → Business Logic → Data → Respond
```

### Your `/analyze` mapped to it:
1. Request arrives (POST /analyze + JSON + `Authorization: Bearer <token>`)
2. Middleware: CORS (origin allowed?) + TrustedHost (Host header ok?)
3. Router matches the endpoint
4. Auth: `get_current_user()` decodes JWT → 401 if bad
5. Validate: `MessageInput` (text 1-5000 chars) → 422 if bad
6. Business: `analyze_text()` → score/label/reasons
7. Data: save `ScanResult` (session.add → commit)
8. Respond: JSON + status 200

---

## Status Codes (with your app)
| Code | Meaning | 401 vs 403 |
|---|---|---|
| 200 | OK | |
| 201 | Created | |
| 400 | Bad request | |
| 401 | **Not authenticated** (who are you?) | ← no/bad token |
| 403 | **Not authorized** (I know you, but no) | |
| 404 | Not found | |
| 422 | Invalid input (validation) | |
| 429 | Rate limited | |

---

## Layering (why files are split)
**Separation of concerns** = one responsibility per layer → changes stay local + easy to test.
- Routing (`main.py`) · Business (`scam_logic.py`) · Data (`database.py`/`models.py`) · Config (`config.py`)
- Bonus: switching SQLite → Postgres = config change only (abstraction).

**Say:** *"I separated routing, business logic, and data access so the app is testable and each piece has one responsibility."*

---

## Auth: Hash vs Encrypt
- **Hash = one-way.** You can only *verify*, never recover the original.
- **Encrypt = reversible.** Needs a key; steal the key → read everything.
- **Passwords → hash.** We never need the original back, and a stolen DB/key exposes nothing.
- bcrypt: slow (hard to brute force) + salted (identical passwords → different hashes).

## JWT Authorization
- Token = `header.payload.signature`, signed with SECRET_KEY.
- Client reads it but can't tamper (signature breaks).
- Server re-computes signature on each request → matches = "I signed this" = trust.
- Trust comes from the SECRET_KEY + crypto, NOT a stored session.
- Sessions = stateful (can revoke instantly) · JWT = stateless (scales, but hard to revoke early).

---

## Security / "production-ready" buzzwords
CORS · input validation · rate limiting (429) · secrets-as-env (fail fast if missing) · health check (`/health`) · trusted hosts · logging.

---

## 30-second project pitch
> "I built a scam-detection API for a React frontend — a layered FastAPI app: routes handle HTTP, a business-logic module scores text, SQLModel handles the database behind a config layer. Auth is bcrypt + stateless JWTs, hardened with CORS, input validation, rate limiting, and fail-fast config. The DB layer is abstracted so I can swap SQLite for Postgres with one config change. Next I'd add Stripe billing, usage quotas, and Redis rate limiting as it scales."

---

## "I don't know" is okay — say it like a pro
> "I'm not 100% sure on that, but here's how I'd reason about it... and I'd verify the docs before shipping."

Interviewers reward the *reasoning*, not perfect recall.

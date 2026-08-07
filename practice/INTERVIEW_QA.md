# Interview Q&A — All Rounds (accumulating)

> Every time you finish a round, its questions + answers get appended here automatically.
> Set 1 = Round 1 (fundamentals) · Set 2 = Round 2 (problem-solving).

---

# SET 1 — Round 1: Fundamentals

## Q1. Walk through what happens when your frontend calls `POST /analyze`.

**Request pipeline (same in almost every backend):**
`Middleware → Auth → Validate → Business Logic → Data → Respond`

1. Request arrives (`POST /analyze` + JSON `{"text": ...}` + `Authorization: Bearer <token>`)
2. Middleware: `CORSMiddleware` (origin allowed?) + `TrustedHostMiddleware` (Host header ok?)
3. Router matches `POST /analyze` → `analyze()` function
4. Auth: `get_current_user()` decodes JWT → **401** if no/invalid token
5. Validate: `MessageInput` (text 1–5000 chars) → **422** if bad
6. Business: `analyze_text()` → score / label / reasons
7. Data: save `ScanResult` (`session.add` → `commit`)
8. Respond: JSON + status **200**

> Note: `/analyze` saves AND returns a result. It does NOT return history — that's a
> separate `GET /history` endpoint.

---

## Q2. What do these status codes mean, and when do you return them?

| Code | Meaning | In your app |
|---|---|---|
| 200 | OK, here's data | `/analyze` success |
| 201 | Created a thing | `/register` |
| 400 | Bad request | duplicate register |
| 401 | **Not authenticated** (who are you?) | `/analyze` with no token |
| 403 | **Not authorized** (I know you, but no) | (future: plan gating) |
| 404 | Not found | bad URL |
| 422 | Invalid input (validation) | weak password |
| 429 | Rate limited | spamming `/register` |

**Trap to avoid:** 401 = not authenticated · 403 = not authorized.

---

## Q3. Why split into `main.py`, `auth.py`, `scam_logic.py`, `database.py`, `models.py`, `config.py`?

**Separation of concerns** — one responsibility per layer → changes stay local, easy to test.
- Routing (`main.py`) · Business (`scam_logic.py`) · Data (`database.py`/`models.py`) · Config (`config.py`)
- Bonus: switching SQLite → Postgres = a config change only (abstraction).

**Say it:** *"I separated routing, business logic, and data access so the app is testable
and each piece has one responsibility."*

---

## Q4. Why store passwords as bcrypt hashes? Hash vs Encrypt?

- **Hash = one-way.** You can only *verify*, never recover the original.
- **Encrypt = reversible.** Needs a key; steal the key → read everything.
- **Passwords → hash.** We never need the original back, and a stolen DB/key exposes nothing.
- Storing plaintext = anyone who reads the DB sees the password.
- bcrypt: slow (hard to brute-force) + salted (identical passwords → different hashes).
- Hashing doesn't stop hashes leaking if DB is stolen — it protects the *plaintext*; attackers
  must brute-force, and bcrypt makes that slow.

---

## Q5. How does the server trust the JWT on the next request? Where does trust come from?

1. At login, the server signs `header.payload.signature` with **SECRET_KEY**.
2. The client can *read* the token but can't *change* it (editing payload breaks the signature).
3. On each request the server **re-computes** the signature → match = "I signed this" = trust.
4. It also checks `exp` (expiry).
- **Trust = SECRET_KEY + cryptography**, not a stored session.
- Sessions = stateful (revoke instantly) · JWT = stateless (scales, hard to revoke early).
- Leak SECRET_KEY → anyone can forge tokens (why it lives in `.env`).

---

# SET 2 — Round 2: Problem-Solving

## P1. "User hammers /analyze-public 1000×/sec. What breaks? What do you do?"

- **Breaks:** endpoint is unauthenticated + does CPU work → attacker can burn CPU / cost you money.
- **Fix (in order):** rate limit by IP (→ **429**), progressive cooldown/temporary block for
  repeat offenders, then require a token for heavy use + monitor/alert.

**Say it:** *"An unauthenticated CPU-heavy endpoint is an abuse target — attackers can cost
you money. I'd rate-limit by IP with a cooldown and escalate to a temporary block for repeat
offenders, and eventually put the heavy work behind authentication."*

---

## P2. "Database got slow. Where do you start?"

1. **Measure first** — log/find the actual slow query, inspect the query plan. Don't guess.
2. **Add indexes** on filtered columns (e.g. `ScanResult.user_id` for `/history`).
3. Only later: caching (Redis), read replicas, connection pooling.

**Say it:** *"I'd log and inspect the slow queries first, then add indexes on the filtered
columns — e.g. I noticed `/history` filters by `user_id`, so I'd index that."*

---

## P3. "User's token expired after 30 min and they're annoyed."

- Add a **refresh token**: long-lived token used ONLY to silently fetch a new access token.
- Access token = short (30 min). Refresh token = long (30 days).
- User is never forced to re-login.

**Say it:** *"I'd add a refresh token — a long-lived token that re-issues a fresh access
token in the background, so users aren't kicked out when the short token expires."*

---

## P4. "Add Free vs Pro plan, Pro = 1000 scans/month. Where in the code?"

| Piece | File | Add |
|---|---|---|
| Store plan | `models.py` | `plan: str = "free"` on `User` |
| Define limits | `config.py` | `FREE_SCANS=100`, `PRO_SCANS=1000` |
| Enforce | `plans.py` / `auth.py` | `check_quota(user)` → count month's `ScanResult` rows → `429/403` |
| Upgrade | route / Stripe webhook | set `user.plan = "pro"` on payment |
| Apply | `main.py` | call `check_quota` inside `analyze` |

**Key insight:** every scan is already in `ScanResult`, so quota = "count the rows."

**Say it:** *"I'd track usage by counting existing scan records per month, gated by a plan
field on the user, and enforce it with a dependency in the analyze endpoint."*

---

## Cheat for the four problem themes
1. **Abuse** → rate limit, auth, backoff. (429)
2. **Slow DB** → measure, index, then cache.
3. **Bad UX on expiry** → refresh tokens.
4. **Paid features** → plan field + count rows + gate with a dependency.


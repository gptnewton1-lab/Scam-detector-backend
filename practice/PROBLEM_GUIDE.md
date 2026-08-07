# Problem-Solving Guide — P1–P4

One-page answers to the "real problem" questions. Read once before bed, once in the morning.

---

## P1 — "User hammers /analyze-public 1000×/sec. What breaks? What do you do?"

**What breaks:** the endpoint is **unauthenticated and does CPU work** → an attacker
can burn your server's CPU and cost you money for free (availability + cost).

**What to do (in order):**
1. **Rate limit by IP** → return **429** after N requests per window. *(You already have this!)*
2. **Progressive cooldown / temporary block** for repeat offenders.
3. Eventually require a token for heavy use; cap payload size; monitor + alert.

**Say it:** *"An unauthenticated CPU-heavy endpoint is an abuse target — attackers can cost you
money. I'd rate-limit by IP with a cooldown and escalate to a temporary block for repeat
offenders, and eventually put the heavy work behind authentication."*

---

## P2 — "Database got slow. Where do you start?"

1. **Measure first — find the actual slow query.** Turn on query logging / look at the
   query plan. Don't guess.
2. **Add indexes** on columns used in `WHERE`/filters.
   - YOUR example: `ScanResult.user_id` is queried by `/history` (`WHERE user_id = ?`)
     but **not indexed** → adding `index=True` speeds it up.
3. Only later: caching (Redis), read replicas, connection pooling.

**Say it:** *"I'd log and inspect the slow queries first, then add indexes on the filtered
columns — e.g. I noticed `/history` filters by `user_id`, so I'd index that."*

---

## P3 — "User's token expired after 30 min and they're annoyed."

**Fix: Refresh tokens.**
- **Access token** (short, ~30 min) → used for API calls.
- **Refresh token** (long, ~30 days) → used ONLY to silently fetch a new access token.

User is never forced to re-login on their phone.

**Say it:** *"I'd add a refresh token — a long-lived token that re-issues a fresh access
token in the background, so users aren't kicked out when the short token expires."*

---

## P4 — "Add Free vs Pro plan, Pro = 1000 scans/month. Where in the code?"

| Piece | File | Add |
|---|---|---|
| Store plan | `models.py` | `plan: str = "free"` on `User` |
| Define limits | `config.py` | `FREE_SCANS=100`, `PRO_SCANS=1000` |
| Enforce | `plans.py` / `auth.py` | `check_quota(user)` → count this month's `ScanResult` rows → `429/403` if over |
| Upgrade | route / Stripe webhook | set `user.plan = "pro"` on payment |
| Apply | `main.py` | call `check_quota` inside `analyze` |

**Key insight:** you already store every scan in `ScanResult`, so **quota = "count the rows."**
No new system needed.

**Say it:** *"I'd track usage by counting existing scan records per month, gated by a plan
field on the user, and enforce it with a dependency in the analyze endpoint."*

---

## Cheat for the four "problem" themes
1. **Abuse** → rate limit, auth, backoff. (429)
2. **Slow DB** → measure, index, then cache.
3. **Bad UX on expiry** → refresh tokens.
4. **Paid features** → plan field on user + count rows for quota + gate with a dependency.

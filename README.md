# Manic AI — Orchestrator

Manic AI is a hierarchical multi-agent orchestration engine. A Manic Chief Agent (CEO) receives a request, delegates to department heads (Coding, Marketing, Growth, Accounting, Sales, Operations), each of which runs its own team, reviews their work, sends it back for fixes if needed, and reports up. The Coding team clones a real repo, writes real files, commits, pushes, and opens a real GitHub PR.

Every request is scoped to one **Organization** (a hard boundary) — no agent, token, or task can cross from one organization into another.

## Architecture

```
                         ┌─────────────────────────┐
                         │   DigiMarkIn Core (hub)  │
                         │   Laravel, issues RS256  │
                         │   JWTs, exposes JWKS      │
                         └────────────┬─────────────┘
                                      │ JWT in Authorization header
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Manic AI Orchestrator (spoke)                    │
│                                                                  │
│  Organizations — DigiMarkIn, LFS Loans, BrightEduAid, Nappilos, │
│                  KwikNap, or any other business you add. Each   │
│                  one is a hard boundary: its own tasks, its     │
│                  own connected GitHub token, nothing shared.    │
│                                                                  │
│  Per organization, a Task fires this tree:                      │
│                                                                  │
│                       Manic Chief Agent                         │
│        ┌──────────┬──────────┬──────────┬──────────┬─────────┐ │
│     Coding     Marketing   Growth    Accounting  Sales   Ops   │
│     (5 agents) (2 agents) (2 agents) (1 agent)  (1 agent)(1)  │
│                                                                  │
│  Every leaf agent has live web access (search + fetch real     │
│  pages). Every manager reviews its team's output and can send  │
│  work back for a specific fix before reporting up.             │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend:** FastAPI + Celery + Redis + PostgreSQL
- **LLM:** Anthropic Claude (claude-sonnet-4-6)
- **Auth:** RS256 JWT verification against DigiMarkIn's JWKS (trustless spoke)
- **Migrations:** Alembic
- **Deploy:** Docker Compose or systemd

## The Org Chart

- **Manic Coding** — Frontend Dev, Backend Dev, Frontend Bug Checker, Backend Bug Checker, Integration Checker. Run sequentially, all building on the same pushed branch. Opens a real PR on approval.
- **Manic Marketing** — Traditional + Digital (content folds into whichever fits).
- **Manic Growth** — Market Researcher + Business Analyst.
- **Manic Accounting** — Bookkeeper (invoicing, expense tracking, filing-prep summaries).
- **Manic Sales** — Sales Rep (lead follow-up, proposals, outreach).
- **Manic Operations** — Ops Coordinator (deadlines, vendor status, rollups).

The Chief Agent only delegates to the teams a given request actually needs.

## Organization Boundary

- `Organization` is its own table. Every `Task` has a required `organization_id`.
- `ConnectedAccount` (GitHub tokens) are keyed on `(user_id, organization_id, provider)` — never on `user_id` alone.
- `get_github_token()` is the *only* function that reads a token, and it always requires both IDs to match.
- Live web browsing is intentionally NOT organization-scoped (it only reads the public internet).

## Run It

```bash
cp .env.example .env   # fill in real values
docker compose up -d --build   # brings up Postgres, Redis, API, and worker
```

Or without Docker, see `deploy/systemd-units.txt` for two long-running services.

### Database Migrations

```bash
# After initial setup:
alembic upgrade head

# After making model changes:
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Environment Variables

See `.env.example` for all required variables:

| Variable | Purpose |
|---|---|
| `DIGIMARKIN_JWKS_URL` | DigiMarkIn Core's JWKS endpoint |
| `DIGIMARKIN_JWT_ISSUER` | JWT issuer claim |
| `DIGIMARKIN_JWT_AUDIENCE` | JWT audience claim |
| `GITHUB_CLIENT_ID` | GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth App client secret |
| `GITHUB_REDIRECT_URI` | OAuth callback URL |
| `ANTHROPIC_API_KEY` | Claude API key |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `TOKEN_ENCRYPTION_KEY` | Fernet key for encrypting stored tokens |
| `MAX_LLM_CALLS_PER_TASK` | Cost control: max Claude calls per task (0 = unlimited) |

## Production Hardening Applied

- **Race condition fix:** Atomic DB guard (`_try_acquire_review`) prevents double-triggering of manager review when sibling tasks finish simultaneously.
- **Redis-backed OAuth state:** OAuth pending states stored in Redis with 10-minute TTL — works across multiple API workers and survives restarts.
- **Path traversal protection:** `write_files()` rejects any file path that resolves outside the repo directory.
- **Celery retries:** `run_agent_node` retries up to 3 times with backoff on transient failures.
- **Structured JSON logging:** All modules emit JSON-formatted logs with task/agent context.
- **Connection pooling:** SQLAlchemy engine configured with `pool_pre_ping`, `pool_size=10`, `max_overflow=20`.
- **Alembic migrations:** Schema evolution handled via Alembic instead of `create_all()`.
- **Cost control:** `MAX_LLM_CALLS_PER_TASK` setting to cap Claude API calls per task.
- **Proper HTTP status codes:** `GET /tasks/{id}` returns 404 (not 200) when not found.
- **Modern FastAPI patterns:** Uses `lifespan` context manager instead of deprecated `@app.on_event`.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/organizations` | Create organization |
| GET | `/organizations` | List organizations for authenticated user |
| POST | `/tasks` | Create task (triggers agent tree) |
| GET | `/tasks/{id}` | Get task with full agent execution tree |
| GET | `/tasks` | List tasks (optional `?organization_id=` filter) |
| GET | `/integrations/github/connect` | Start GitHub OAuth flow |
| GET | `/integrations/github/callback` | OAuth callback |

All endpoints except `/health` require a valid DigiMarkIn JWT in the `Authorization: Bearer` header.

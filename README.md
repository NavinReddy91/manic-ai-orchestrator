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
- **LLM:** Multi-provider (Groq, Gemini, OpenAI, Anthropic, OpenRouter)
- **Auth:** RS256 JWT verification against DigiMarkIn's JWKS (trustless spoke)
- **Migrations:** Alembic
- **Deploy:** Docker Compose or systemd

## LLM Providers

The system supports multiple LLM backends. Set `LLM_PROVIDER` in `.env`:

| Provider | `LLM_PROVIDER` | Example `LLM_MODEL` | Notes |
|---|---|---|---|
| **Groq** | `groq` | `llama-3.3-70b-versatile` | Fast, cheap, good for testing |
| **Google Gemini** | `gemini` | `gemini-2.0-flash` | Good balance of speed/quality |
| **OpenAI** | `openai` | `gpt-4o` | High quality, higher cost |
| **Anthropic** | `anthropic` | `claude-sonnet-4-6` | High quality, higher cost |
| **OpenRouter** | `openrouter` | `anthropic/claude-3.5-sonnet` | Access to many models via one API |

**Recommendation for testing:** Start with Groq (`llama-3.3-70b-versatile`) — it's fast and cheap. Switch to Gemini or GPT-4o for production when you need higher quality.

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

## Deployment Guide

### Option 1: Docker Compose (Recommended)

```bash
cp .env.example .env   # fill in real values
docker compose up -d --build   # brings up Postgres, Redis, API, and worker
```

This runs 4 services:
- `postgres` — PostgreSQL database
- `redis` — Redis for Celery task queue
- `api` — FastAPI web server (port 8010)
- `worker` — Celery worker (processes agent tasks)

### Option 2: Systemd (No Docker)

See `deploy/systemd-units.txt` for two long-running services.

### Where to Deploy

| Option | Cost | Best For |
|---|---|---|
| **Same VPS as DigiMarkIn** | $0 extra | If your Laravel server has 2GB+ free RAM |
| **Cheap VPS** | $5-12/mo | Dedicated server (Hetzner €4/mo, DigitalOcean $6/mo) |
| **Render (paid)** | ~$25-40/mo | Managed hosting, but pricey for Celery |
| **Render (free)** | $0 | **Not viable** — no persistent Redis/Postgres, workers spin down |

**Recommendation:** Deploy on the same VPS as DigiMarkIn (if resources allow) or get a cheap VPS with 2GB+ RAM. Free tiers won't work reliably for a Celery-based system.

### Integrating with DigiMarkIn (Laravel)

**Do NOT embed this inside Laravel.** They are different languages and runtimes. The hub-and-spoke design is correct:

1. **DigiMarkIn (Laravel)** — Your admin panel, user login, dashboard
2. **Manic AI Orchestrator (Python)** — Agent execution, git operations, LLM calls

**How they communicate:**
- Laravel admin panel has a "Manic AI" page
- User types a prompt, clicks send
- Laravel backend sends `POST https://your-orchestrator-url/tasks` with the JWT
- Orchestrator processes in background, returns task ID
- Laravel polls `GET /tasks/{id}` to show progress
- When done, Laravel displays the final report

**CORS:** Update `app/main.py` to allow your DigiMarkIn domain:
```python
allow_origins=["https://digimarkin.com", "https://admin.digimarkin.com"]
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
| `LLM_PROVIDER` | LLM provider (groq, gemini, openai, anthropic, openrouter) |
| `LLM_API_KEY` | API key for the chosen provider |
| `LLM_MODEL` | Model name (e.g., llama-3.3-70b-versatile) |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `TOKEN_ENCRYPTION_KEY` | Fernet key for encrypting stored tokens |
| `MAX_LLM_CALLS_PER_TASK` | Cost control: max LLM calls per task (0 = unlimited) |

## Database Migrations

```bash
# After initial setup:
alembic upgrade head

# After making model changes:
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Production Hardening Applied

- **Race condition fix:** Atomic DB guard (`_try_acquire_review`) prevents double-triggering of manager review when sibling tasks finish simultaneously.
- **Redis-backed OAuth state:** OAuth pending states stored in Redis with 10-minute TTL — works across multiple API workers and survives restarts.
- **Path traversal protection:** `write_files()` rejects any file path that resolves outside the repo directory.
- **Celery retries:** `run_agent_node` retries up to 3 times with backoff on transient failures.
- **Structured JSON logging:** All modules emit JSON-formatted logs with task/agent context.
- **Connection pooling:** SQLAlchemy engine configured with `pool_pre_ping`, `pool_size=10`, `max_overflow=20`.
- **Alembic migrations:** Schema evolution handled via Alembic instead of `create_all()`.
- **Cost control:** `MAX_LLM_CALLS_PER_TASK` setting to cap LLM API calls per task.
- **Multi-provider LLM:** Switch between Groq, Gemini, OpenAI, Anthropic, or OpenRouter via environment config.
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

## Testing Locally

1. Copy `.env.example` to `.env` and fill in values
2. Get a Groq API key from https://console.groq.com (free tier available)
3. Run `docker compose up -d --build`
4. Test health: `curl http://localhost:8010/health`
5. Create a task via API (requires a valid JWT or temporarily disable auth for testing)

## Next Steps

- [ ] Set up DigiMarkIn's JWKS endpoint (if not already done)
- [ ] Create GitHub OAuth App at https://github.com/settings/developers
- [ ] Deploy orchestrator to VPS
- [ ] Add "Manic AI" page to DigiMarkIn admin panel
- [ ] Test with a simple non-coding task (marketing or research)
- [ ] Test with a coding task against a throwaway test repo
- [ ] Verify organization boundary isolation
- [ ] Switch to production LLM provider (Gemini or GPT-4o)

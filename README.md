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

## Features

### Core Features
- **Hierarchical agent system** — CEO → 6 department heads → 10 leaf workers
- **Real git operations** — clone, branch, write files, commit, push, open PR
- **Live web access** — DuckDuckGo search + page fetch for all leaf agents
- **Organization boundary enforcement** — hard isolation between businesses
- **Multi-provider LLM** — switch between Groq, Gemini, OpenAI, Anthropic, or OpenRouter

### Production Hardening
- **Task cancellation** — cancel running tasks via `DELETE /tasks/{id}`
- **Task timeouts** — auto-fail tasks stuck in "running" for too long (configurable)
- **Webhook callbacks** — POST task results to a URL when tasks complete
- **Rate limiting** — per-user limits on task creation (per-minute and per-hour)
- **Error recovery** — background job detects and fails stale tasks
- **Admin/debug endpoints** — view all tasks, stats, audit logs without JWT
- **Audit logging** — track who created/cancelled tasks, when, from which IP
- **Task templates** — save and reuse common prompts
- **Agent customization** — per-organization overrides for agent system prompts
- **File size limits** — prevent coding agents from writing huge files
- **Branch naming conflicts** — unique branch names for concurrent tasks
- **Task prioritization** — normal, high, or urgent priority levels
- **Cost tracking** — track LLM call count and estimated token usage per task
- **Race condition fix** — atomic DB guard prevents double-triggering of manager review
- **Redis-backed OAuth state** — works across multiple API workers
- **Path traversal protection** — rejects file paths outside repo directory
- **Celery retries** — automatic retry with backoff on transient failures
- **Structured JSON logging** — all modules emit JSON-formatted logs
- **Connection pooling** — SQLAlchemy configured for production

## LLM Providers

Set `LLM_PROVIDER` in `.env`:

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

**Recommendation:** Deploy on the same VPS as DigiMarkIn (if resources allow) or get a cheap VPS with 2GB+ RAM.

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

**Or use webhooks:**
- Pass `callback_url` when creating a task
- Orchestrator POSTs the result to that URL when the task completes
- No polling needed

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
| `RATE_LIMIT_TASKS_PER_MINUTE` | Max tasks per user per minute |
| `RATE_LIMIT_TASKS_PER_HOUR` | Max tasks per user per hour |
| `TASK_TIMEOUT_MINUTES` | Auto-fail tasks stuck in "running" for this long |
| `ADMIN_SECRET` | Bearer token for /admin endpoints |
| `ADMIN_ALLOWED_IPS` | Comma-separated IPs allowed to access /admin |
| `MAX_FILE_SIZE_BYTES` | Max file size for coding agents (default 1MB) |
| `MAX_FILES_PER_COMMIT` | Max files in a single commit (default 50) |

## API Endpoints

### Tasks
| Method | Path | Description |
|---|---|---|
| POST | `/tasks` | Create task (with optional `callback_url`, `priority`) |
| GET | `/tasks/{id}` | Get task with full agent execution tree |
| GET | `/tasks` | List tasks (optional `?organization_id=` and `?status=` filters) |
| DELETE | `/tasks/{id}` | Cancel a running task |

### Organizations
| Method | Path | Description |
|---|---|---|
| POST | `/organizations` | Create organization |
| GET | `/organizations` | List organizations for authenticated user |

### Task Templates
| Method | Path | Description |
|---|---|---|
| POST | `/task-templates` | Create a task template |
| GET | `/task-templates` | List templates (optional `?organization_id=` filter) |
| GET | `/task-templates/{id}` | Get a specific template |
| PUT | `/task-templates/{id}` | Update a template |
| DELETE | `/task-templates/{id}` | Delete a template |

### GitHub Integration
| Method | Path | Description |
|---|---|---|
| GET | `/integrations/github/connect` | Start GitHub OAuth flow |
| GET | `/integrations/github/callback` | OAuth callback |

### Admin (requires `ADMIN_SECRET` or IP whitelist)
| Method | Path | Description |
|---|---|---|
| GET | `/admin/tasks` | List all tasks across all organizations |
| GET | `/admin/tasks/stale` | List tasks stuck in "running" for too long |
| GET | `/admin/stats` | System-wide statistics |
| GET | `/admin/audit` | Audit logs with filters |

### Health
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |

All endpoints except `/health` and `/admin/*` require a valid DigiMarkIn JWT in the `Authorization: Bearer` header.

## Database Migrations

```bash
# After initial setup:
alembic upgrade head

# After making model changes:
alembic revision --autogenerate -m "description"
alembic upgrade head
```

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
- [ ] Configure webhooks for real-time task completion notifications
- [ ] Set up admin endpoints for monitoring and debugging

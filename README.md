# Sonic AI Orchestrator

**Multi-agent AI orchestration engine with hierarchical task delegation**

Sonic AI is a standalone, deployable multi-agent system where a Chief Agent delegates tasks to department heads (Coding, Marketing, Growth, Accounting, Sales, Operations), each managing their own team of specialists. The system reviews work, sends it back for fixes if needed, and compiles final reports.

## 🚀 Quick Start

### Deploy to Render (Free Tier)

1. **Fork this repo** or use directly: `https://github.com/NavinReddy91/sonic-ai-orchestrator`

2. **Go to Render Dashboard** → Blueprints → New Blueprint Instance

3. **Connect your GitHub repo**

4. **Set environment variables** in Render dashboard:
   ```bash
   LLM_API_KEY=your_groq_api_key  # Get from https://console.groq.com
   API_KEY=your_custom_api_key     # Optional: protects your API
   ```

5. **Deploy!** Render will create:
   - Web service (API)
   - Background worker (Celery)
   - PostgreSQL database
   - Redis

### Local Development

```bash
# Clone the repo
git clone https://github.com/NavinReddy91/sonic-ai-orchestrator.git
cd sonic-ai-orchestrator

# Create .env file
cp .env.example .env
# Edit .env and add your LLM_API_KEY

# Start with Docker Compose
docker compose up -d

# Or run locally
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Test It

```bash
# Health check
curl http://localhost:8000/health

# Create an organization
curl -X POST http://localhost:8000/organizations \
  -H "Content-Type: application/json" \
  -d '{"name": "My Business"}'

# Create a task
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "your-org-id",
    "prompt": "Research the latest AI trends for 2024"
  }'

# Check task status
curl http://localhost:8000/tasks/{task_id}
```

## 🏗️ Architecture

```
                    ┌─────────────────────┐
                    │   Sonic AI Chief    │
                    │     (CEO Agent)     │
                    └──────────┬──────────┘
                               │
        ┌──────────┬───────────┼───────────┬──────────┬──────────┐
        │          │           │           │          │          │
   ┌────▼────┐ ┌──▼───┐  ┌───▼────┐  ┌───▼────┐ ┌──▼───┐ ┌───▼────┐
   │ Coding  │ │Mktg  │  │ Growth │  │Account │ │Sales │ │  Ops   │
   │  Team   │ │ Team │  │  Team  │  │  Team  │ │ Team │ │  Team  │
   │(5 agents│ │(2)   │  │  (2)   │  │  (1)   │ │ (1)  │ │  (1)   │
   └─────────┘ └──────┘  └────────┘  └────────┘ └──────┘ └────────┘
```

### Agent Teams

- **Coding Team** (5 agents) — Frontend Dev, Backend Dev, Bug Checkers, Integration Checker
  - Sequential execution (frontend → backend → bug checks → integration)
  - Can clone repos, write code, commit, push, and open PRs
  - Requires GitHub OAuth integration

- **Marketing Team** (2 agents) — Traditional Marketing, Digital Marketing
  - Parallel execution
  - Can search the web for research

- **Growth Team** (2 agents) — Market Researcher, Business Analyst
  - Parallel execution
  - Can search the web for research

- **Accounting Team** (1 agent) — Bookkeeper
  - Invoicing, expense tracking, filing prep

- **Sales Team** (1 agent) — Sales Rep
  - Lead follow-up, proposals, outreach

- **Operations Team** (1 agent) — Ops Coordinator
  - Deadlines, vendor status, rollups

## 🤖 LLM Providers

Sonic AI supports multiple LLM backends. Set `LLM_PROVIDER` in `.env`:

| Provider | `LLM_PROVIDER` | Example `LLM_MODEL` | Notes |
|----------|----------------|---------------------|-------|
| **Groq** | `groq` | `llama-3.3-70b-versatile` | Fast, cheap, free tier |
| **Google Gemini** | `gemini` | `gemini-2.0-flash` | Good balance |
| **OpenAI** | `openai` | `gpt-4o` | High quality |
| **Anthropic** | `anthropic` | `claude-sonnet-4-6` | High quality |
| **OpenRouter** | `openrouter` | `anthropic/claude-3.5-sonnet` | Many models |
| **Local (Ollama)** | `local` | `qwen2.5:3b` | Self-hosted, free |

### Using Local Models (Ollama)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull qwen2.5:3b

# Configure Sonic AI
LLM_PROVIDER=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
LLM_API_KEY=  # Leave empty for local
```

## 🔐 Authentication

### No Auth (Development)
Leave `API_KEY` empty in `.env` — all endpoints are open.

### API Key Auth (Production)
Set `API_KEY` in `.env`:
```bash
API_KEY=your-secret-key-here
```

Then include in requests:
```bash
curl -H "X-API-Key: your-secret-key-here" http://localhost:8000/tasks
```

## 📡 API Endpoints

### Tasks
- `POST /tasks` — Create a new task
- `GET /tasks/{id}` — Get task status and results
- `GET /tasks` — List all tasks
- `DELETE /tasks/{id}` — Cancel a running task

### Organizations
- `POST /organizations` — Create an organization
- `GET /organizations` — List organizations

### Task Templates
- `POST /task-templates` — Save a task template
- `GET /task-templates` — List templates
- `PUT /task-templates/{id}` — Update template
- `DELETE /task-templates/{id}` — Delete template

### GitHub Integration (Optional)
- `GET /integrations/github/connect` — Start OAuth flow
- `GET /integrations/github/callback` — OAuth callback

### Admin (Optional)
- `GET /admin/tasks` — List all tasks (requires `ADMIN_SECRET`)
- `GET /admin/tasks/stale` — Find stuck tasks
- `GET /admin/stats` — System statistics
- `GET /admin/audit` — Audit logs

### Health
- `GET /health` — Health check
- `GET /` — API info

## 🎯 Features

### Core Features
- ✅ **Hierarchical agent system** — CEO → 6 department heads → 10 leaf workers
- ✅ **Multi-provider LLM** — Groq, Gemini, OpenAI, Anthropic, OpenRouter, or local
- ✅ **Live web access** — DuckDuckGo search + page fetch for research
- ✅ **Organization boundaries** — Hard isolation between businesses
- ✅ **Real git operations** — Clone, branch, write, commit, push, open PRs

### Production Features
- ✅ **Task cancellation** — Cancel running tasks
- ✅ **Task timeouts** — Auto-fail stuck tasks
- ✅ **Webhook callbacks** — POST results to your URL
- ✅ **Rate limiting** — Per-user limits
- ✅ **Audit logging** — Track all actions
- ✅ **Task templates** — Save and reuse prompts
- ✅ **Agent customization** — Per-org prompt overrides
- ✅ **Cost tracking** — LLM call count + token estimates
- ✅ **File size limits** — Prevent huge files
- ✅ **Race condition protection** — Atomic DB guards

## 📦 Deployment Options

### Render (Recommended for Testing)
- Free tier available
- Managed PostgreSQL + Redis
- Automatic HTTPS
- See `RENDER_DEPLOYMENT.md` for details

### Docker Compose (VPS/Self-Hosted)
```bash
docker compose up -d
```
- Full control
- Use your own PostgreSQL/Redis or built-in
- Connect to local LLM (Ollama)

### Manual Deployment
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
celery -A app.worker.celery_app worker --loglevel=info
```

## 🔧 Configuration

See `.env.example` for all options. Key settings:

```bash
# Required
LLM_API_KEY=your-api-key

# Optional
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
API_KEY=your-secret-key
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
ADMIN_SECRET=your-admin-secret
```

## 🧪 Testing

### Test with Groq (Free)
1. Get API key from https://console.groq.com
2. Set `LLM_PROVIDER=groq` and `LLM_API_KEY=...`
3. Create a task — should complete in seconds

### Test with Local Model
1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull model: `ollama pull qwen2.5:3b`
3. Set `LLM_PROVIDER=local` and `LLM_BASE_URL=http://localhost:11434/v1`
4. Create a task — works offline!

### Test Coding Tasks
1. Set up GitHub OAuth (see GitHub Integration below)
2. Connect a repo: `GET /integrations/github/connect?organization_id=...`
3. Create a coding task:
   ```json
   {
     "organization_id": "...",
     "prompt": "Add a README file with project description",
     "repo": "username/repo"
   }
   ```

## 🔗 GitHub Integration (Optional)

For coding tasks, connect GitHub:

1. **Create GitHub OAuth App** at https://github.com/settings/developers
   - Homepage URL: `http://localhost:8000`
   - Callback URL: `http://localhost:8000/integrations/github/callback`

2. **Set environment variables**:
   ```bash
   GITHUB_CLIENT_ID=your-client-id
   GITHUB_CLIENT_SECRET=your-client-secret
   GITHUB_REDIRECT_URI=http://localhost:8000/integrations/github/callback
   ```

3. **Connect a repo**:
   ```bash
   curl "http://localhost:8000/integrations/github/connect?organization_id=YOUR_ORG_ID"
   ```

## 📊 Monitoring

### Check Logs
```bash
# Docker Compose
docker compose logs -f api
docker compose logs -f worker

# Render
# View logs in Render dashboard
```

### Admin Endpoints
Set `ADMIN_SECRET` and access:
- `/admin/tasks` — All tasks
- `/admin/tasks/stale` — Stuck tasks
- `/admin/stats` — Statistics
- `/admin/audit` — Audit logs

## 🛠️ Development

### Project Structure
```
sonic-ai-orchestrator/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── models.py            # Database models
│   ├── auth.py              # Authentication
│   ├── db.py                # Database setup
│   ├── worker.py            # Celery worker (core engine)
│   ├── llm.py               # LLM provider abstraction
│   ├── org_chart.py         # Agent hierarchy
│   ├── tasks_api.py         # Task endpoints
│   ├── organizations_api.py # Organization endpoints
│   ├── github_oauth.py      # GitHub integration
│   ├── admin_api.py         # Admin endpoints
│   ├── task_templates_api.py# Template endpoints
│   ├── rate_limiter.py      # Rate limiting
│   ├── audit.py             # Audit logging
│   ├── webhook.py           # Webhook callbacks
│   ├── task_timeout.py      # Stale task cleanup
│   ├── git_ops.py           # Git operations
│   ├── web_tools.py         # Web search/fetch
│   └── logging_config.py    # Logging setup
├── alembic/                 # Database migrations
├── docker-compose.yml       # Docker setup
├── render.yaml              # Render blueprint
├── requirements.txt         # Python dependencies
└── .env.example             # Environment template
```

### Run Tests
```bash
pytest tests/
```

### Database Migrations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## 💡 Use Cases

1. **Content Creation** — "Write a blog post about AI trends"
2. **Market Research** — "Research competitors in the CRM space"
3. **Code Development** — "Add user authentication to my app"
4. **Marketing Strategy** — "Create a social media campaign"
5. **Business Analysis** — "Analyze our Q4 sales data"
6. **Operations** — "Track vendor deadlines for next month"

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License — see LICENSE file for details

## 🆘 Support

- **Documentation**: See `RENDER_DEPLOYMENT.md` and `QUICK_START.md`
- **Issues**: https://github.com/NavinReddy91/sonic-ai-orchestrator/issues
- **Email**: support@sonic-ai.com

## 🎉 Credits

Built with:
- FastAPI — Web framework
- Celery — Task queue
- SQLAlchemy — ORM
- Redis — Message broker
- PostgreSQL / SQLite — Database
- Anthropic / OpenAI / Groq / Google — LLM providers

---

**Ready to deploy?** Check out [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for step-by-step instructions.

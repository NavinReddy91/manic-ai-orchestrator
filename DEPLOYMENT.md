# Sonic AI Orchestrator - Deployment Guide

## ✅ What Changed

Your project has been completely rebranded and simplified:

### Before (Manic AI)
- ❌ Required DigiMarkIn JWT authentication
- ❌ Hub-spoke architecture with external dependencies
- ❌ Complex setup with multiple required services
- ❌ Hard to deploy standalone

### After (Sonic AI)
- ✅ **Standalone** - no external dependencies
- ✅ **Simple API key auth** - or no auth for testing
- ✅ **Render-ready** - deploys on free tier
- ✅ **Self-contained** - SQLite for dev, PostgreSQL for prod
- ✅ **Optional GitHub** - only needed for coding tasks

---

## 🚀 Deploy to Render (Free Tier)

### Step 1: Go to Render
1. Visit https://dashboard.render.com
2. Sign up / Log in
3. Click "New +" → "Blueprint"

### Step 2: Connect GitHub
1. Connect your GitHub account
2. Select repository: `NavinReddy91/manic-ai-orchestrator`
3. Render will detect `render.yaml` automatically

### Step 3: Configure Environment Variables
In Render dashboard, set these:

**Required:**
```bash
LLM_API_KEY=your_groq_api_key_here
```
Get your free Groq API key at: https://console.groq.com

**Optional:**
```bash
API_KEY=your_custom_secret_key  # Protects your API (leave empty for open access)
ADMIN_SECRET=your_admin_secret   # Protects /admin endpoints
```

### Step 4: Deploy
Click "Apply" and wait 2-3 minutes for deployment.

Render will create:
- ✅ Web service (API) - Free tier
- ✅ Background worker (Celery) - Free tier
- ✅ PostgreSQL database - Free tier (90 days)
- ✅ Redis - Free tier (90 days)

### Step 5: Test
```bash
# Get your Render URL from dashboard
curl https://sonic-ai-api.onrender.com/health

# Should return:
{"status":"ok","service":"sonic-ai-orchestrator","version":"1.0.0"}
```

---

## 🧪 Test Your Deployment

### Create an Organization
```bash
curl -X POST https://your-app.onrender.com/organizations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"name": "My Business"}'
```

Save the `id` from the response.

### Create a Task
```bash
curl -X POST https://your-app.onrender.com/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "organization_id": "your-org-id-here",
    "prompt": "Research the latest AI trends for 2024 and create a summary"
  }'
```

### Check Task Status
```bash
curl https://your-app.onrender.com/tasks/{task-id} \
  -H "X-API-Key: your-api-key"
```

Wait 30-60 seconds, then check again. You'll see:
- Agent hierarchy being created
- Each agent's status (pending → running → done)
- Final report when complete

---

## 🏠 Local Development

### Option 1: Docker Compose (Recommended)
```bash
# Clone the repo
git clone https://github.com/NavinReddy91/manic-ai-orchestrator.git
cd manic-ai-orchestrator

# Create .env file
cp .env.example .env
# Edit .env and add your LLM_API_KEY

# Start everything
docker compose up -d

# View logs
docker compose logs -f api
```

Access at: http://localhost:8000

### Option 2: Run Locally (No Docker)
```bash
# Install dependencies
pip install -r requirements.txt

# Install Redis (if not installed)
# macOS: brew install redis
# Ubuntu: sudo apt install redis-server

# Start Redis
redis-server

# Create .env
cp .env.example .env
# Edit .env and add your LLM_API_KEY

# Start API
uvicorn app.main:app --reload --port 8000

# In another terminal, start worker
celery -A app.worker.celery_app worker --loglevel=info
```

---

## 🤖 LLM Provider Options

### Groq (Recommended - Free)
```bash
LLM_PROVIDER=groq
LLM_API_KEY=gsk_xxxxx  # Get from https://console.groq.com
LLM_MODEL=llama-3.3-70b-versatile
```
✅ Free tier available
✅ Fast (500+ tokens/sec)
✅ Good quality

### Google Gemini (Free)
```bash
LLM_PROVIDER=gemini
LLM_API_KEY=AIxxxxx  # Get from https://aistudio.google.com/apikey
LLM_MODEL=gemini-2.0-flash
```
✅ Free tier available
✅ Good quality
✅ Large context window

### Local (Ollama) - Completely Free
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull qwen2.5:3b

# Configure
LLM_PROVIDER=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
LLM_API_KEY=  # Leave empty
```
✅ 100% free
✅ Works offline
✅ Private
⚠️ Slower
⚠️ Lower quality (3B model)

---

## 🔐 Authentication

### No Auth (Testing)
Leave `API_KEY` empty in `.env` - all endpoints are open.

### API Key Auth (Production)
```bash
API_KEY=your-secret-key-here
```

Then include in all requests:
```bash
curl -H "X-API-Key: your-secret-key-here" https://your-app.onrender.com/tasks
```

---

## 📊 Features Overview

### Core Features
- ✅ Hierarchical multi-agent system (CEO → 6 departments → 10 workers)
- ✅ Multi-LLM support (Groq, Gemini, OpenAI, Anthropic, local)
- ✅ Live web research (DuckDuckGo search + page fetch)
- ✅ Organization boundaries (hard isolation)
- ✅ Task templates (save and reuse prompts)
- ✅ Audit logging (track all actions)

### Production Features
- ✅ Task cancellation (stop running tasks)
- ✅ Task timeouts (auto-fail stuck tasks)
- ✅ Webhook callbacks (POST results to your URL)
- ✅ Rate limiting (prevent abuse)
- ✅ Cost tracking (LLM call count + token estimates)
- ✅ File size limits (prevent huge files)
- ✅ Admin endpoints (monitor and debug)

### Optional Features
- ⚙️ GitHub integration (for coding tasks)
- ⚙️ Per-org agent customization
- ⚙️ Priority queues

---

## 🎯 Use Cases

### 1. Content Creation
```bash
curl -X POST https://your-app.onrender.com/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "org-id",
    "prompt": "Write a blog post about AI trends in 2024"
  }'
```

### 2. Market Research
```bash
curl -X POST https://your-app.onrender.com/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "org-id",
    "prompt": "Research competitors in the CRM software space"
  }'
```

### 3. Marketing Strategy
```bash
curl -X POST https://your-app.onrender.com/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "org-id",
    "prompt": "Create a social media marketing campaign for a new product launch"
  }'
```

### 4. Code Development (Requires GitHub)
```bash
curl -X POST https://your-app.onrender.com/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "org-id",
    "prompt": "Add user authentication to my Express.js app",
    "repo": "username/repo-name"
  }'
```

---

## 🐛 Troubleshooting

### "LLM_API_KEY not set"
- Add `LLM_API_KEY` to Render environment variables
- Restart the service

### "Task stuck in running"
- Check worker logs in Render dashboard
- Verify Redis is running
- Check LLM API key is valid

### "Database connection failed"
- On Render: Check database is provisioned
- Locally: Verify PostgreSQL is running

### "Rate limit exceeded"
- Wait a minute and try again
- Increase `RATE_LIMIT_TASKS_PER_MINUTE` in .env

---

## 📚 API Documentation

Interactive API docs available at:
- Local: http://localhost:8000/docs
- Render: https://your-app.onrender.com/docs

---

## 💰 Cost Estimation

### Render Free Tier
- ✅ Web service: Free (spins down after 15 min inactivity)
- ✅ Worker: Free (spins down after 15 min inactivity)
- ✅ PostgreSQL: Free for 90 days, then $7/month
- ✅ Redis: Free for 90 days, then $10/month

**Total after 90 days: ~$17/month**

### LLM Costs
- **Groq**: Free tier (limited), then $0.20 per 1M tokens
- **Gemini**: Free tier (limited), then $0.000125 per 1K tokens
- **Local (Ollama)**: $0 (your hardware)

**Typical task cost: $0.01 - $0.10** (depending on complexity)

---

## 🎓 Next Steps

1. ✅ Deploy to Render
2. ✅ Test with a simple task
3. ✅ Try different LLM providers
4. ⏳ Set up GitHub integration (for coding tasks)
5. ⏳ Build a frontend UI
6. ⏳ Integrate with your existing apps

---

## 🆘 Support

- **GitHub Issues**: https://github.com/NavinReddy91/manic-ai-orchestrator/issues
- **Render Docs**: https://render.com/docs
- **Groq Docs**: https://console.groq.com/docs

---

## 🎉 You're Ready!

Your Sonic AI Orchestrator is now:
- ✅ Completely standalone
- ✅ Ready for Render deployment
- ✅ Free tier compatible
- ✅ Production-ready features
- ✅ Easy to customize

**Deploy now and start building!** 🚀

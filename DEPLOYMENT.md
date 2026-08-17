# Manic AI Orchestrator - Deployment Guide

## What Changed

Your project has been completely rebranded and simplified for easy deployment:

### Before
- ❌ Required Celery + Redis worker
- ❌ Complex multi-service deployment
- ❌ PostgreSQL required
- ❌ No frontend UI

### After
- ✅ **Single process** - No Celery/Redis needed for basic deployment
- ✅ **Render free tier ready** - Deploys on free tier with NeonDB
- ✅ **Sci-fi frontend** - Beautiful command center UI included
- ✅ **NeonDB integration** - Free PostgreSQL for production

---

## Deploy to Render (Free Tier) - 2 Minutes

### Step 1: Get LLM API Key
1. Visit https://console.groq.com
2. Sign up (free tier available)
3. Create an API key

### Step 2: Get NeonDB Connection String
1. Visit https://neon.tech
2. Sign up (free tier: 0.5 GB storage)
3. Create a new project
4. Copy the connection string (looks like: `postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`)

### Step 3: Deploy on Render
1. Go to https://dashboard.render.com
2. Click "New +" → "Blueprint"
3. Connect GitHub repository: `NavinReddy91/manic-ai-orchestrator`
4. Render will detect `render.yaml` automatically
5. Set environment variables:
   - **LLM_API_KEY**: Your Groq API key (required)
   - **DATABASE_URL**: Your NeonDB connection string (required)
6. Click "Apply"

### Step 4: Test
```bash
# Get your Render URL from dashboard
curl https://manic-ai-api.onrender.com/health

# Should return:
{"status":"ok","service":"manic-ai-orchestrator","version":"1.0.0"}
```

### Step 5: Access the UI
Open your Render URL in a browser to access the sci-fi command center UI.

---

## Environment Variables

### Required
```bash
LLM_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
```

### Optional
```bash
# LLM Provider (default: groq)
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile

# API Authentication (leave empty for open access)
API_KEY=your_secret_key

# Admin endpoints protection
ADMIN_SECRET=your_admin_secret
```

---

## LLM Provider Options

### Groq (Recommended - Free)
```bash
LLM_PROVIDER=groq
LLM_API_KEY=gsk_xxxxx
LLM_MODEL=llama-3.3-70b-versatile
```
- Free tier available
- Fast (500+ tokens/sec)
- Good quality

### Google Gemini (Free)
```bash
LLM_PROVIDER=gemini
LLM_API_KEY=AIxxxxx
LLM_MODEL=gemini-2.0-flash
```
- Free tier available
- Good quality
- Large context window

### OpenAI (GPT-4)
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxxxx
LLM_MODEL=gpt-4o
```

### Anthropic (Claude)
```bash
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-sonnet-4-6
```

### Local (Ollama) - Completely Free
```bash
LLM_PROVIDER=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
```
- 100% free
- Works offline
- Private

---

## Local Development

### Option 1: Run Directly
```bash
# Clone
git clone https://github.com/NavinReddy91/manic-ai-orchestrator.git
cd manic-ai-orchestrator

# Install dependencies
pip install -r requirements.txt

# Create .env
cp .env.example .env
# Edit .env and add your LLM_API_KEY

# Start server
uvicorn app.main:app --reload --port 8000
```

Access at: http://localhost:8000

### Option 2: Docker Compose
```bash
# Clone and configure
git clone https://github.com/NavinReddy91/manic-ai-orchestrator.git
cd manic-ai-orchestrator
cp .env.example .env
# Edit .env

# Start everything
docker compose up -d

# View logs
docker compose logs -f api
```

---

## API Usage

### Create an Organization
```bash
curl -X POST https://your-app.onrender.com/organizations \
  -H "Content-Type: application/json" \
  -d '{"name": "My Business"}'
```

### Create a Task
```bash
curl -X POST https://your-app.onrender.com/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "your-org-id",
    "prompt": "Research AI trends and create a strategy document"
  }'
```

### Check Task Status
```bash
curl https://your-app.onrender.com/tasks/{task-id}
```

---

## Architecture

### Single Process Mode (Default)
- FastAPI handles API requests
- Background tasks run in-process using asyncio
- SQLite database (or PostgreSQL if configured)
- No external dependencies required

### Multi-Process Mode (Optional)
For high-traffic deployments, you can enable Celery:
1. Uncomment `celery` and `redis` in `requirements.txt`
2. Set `REDIS_URL` environment variable
3. Run worker: `celery -A app.worker.celery_app worker`

---

## Frontend

The project includes a sci-fi themed command center UI inspired by stonicai.com:
- Real-time task monitoring
- Agent hierarchy visualization
- Mission control interface
- Dark theme with animations

Access the UI at the root URL of your deployment.

---

## Troubleshooting

### "could not translate host name" or PostgreSQL connection errors
- Check that `DATABASE_URL` is correctly set in Render environment variables
- Verify your NeonDB connection string includes `?sslmode=require`
- Example: `postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`
- Check NeonDB dashboard to ensure your project is active

### "LLM_API_KEY not set"
- Add `LLM_API_KEY` to Render environment variables
- Restart the service

### "Task stuck in running"
- Check server logs
- Verify LLM API key is valid
- Check LLM provider status

### "Database connection failed"
- Verify `DATABASE_URL` is set correctly in Render environment variables
- Check NeonDB connection string format
- Ensure NeonDB project is not paused (free tier projects pause after inactivity)
- Check Render logs for specific error messages

### Frontend not loading
- Ensure `frontend/` directory exists
- Check that static files are being served

---

## Cost Estimation

### Render Free Tier + NeonDB Free Tier
- Web service: Free (spins down after 15 min inactivity)
- NeonDB: Free (0.5 GB storage, unlimited projects)
- **Total: $0/month**

### LLM Costs
- Groq: Free tier (limited), then $0.20 per 1M tokens
- Gemini: Free tier (limited), then pay-per-use
- **Typical task cost: $0.01 - $0.10**

---

## Support

- **GitHub Issues**: https://github.com/NavinReddy91/manic-ai-orchestrator/issues
- **API Documentation**: Available at `/docs` endpoint
- **Render Docs**: https://render.com/docs

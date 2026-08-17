# Render Deployment Guide - Manic AI Orchestrator

This guide walks you through deploying Manic AI on Render.com step by step.

## Prerequisites

- Render account (free tier works for testing)
- Groq API key (free tier available at https://console.groq.com)
- GitHub account with this repo

## Step 1: Create Render Services

### Option A: Using Blueprint (Recommended)

1. Go to https://dashboard.render.com/blueprints
2. Click "New Blueprint Instance"
3. Connect your GitHub repo: `NavinReddy91/manic-ai-orchestrator`
4. Render will detect `render.yaml` and create all services automatically
5. Set required environment variables (see Step 2)
6. Click "Apply"

### Option B: Manual Setup

Create these services manually in Render dashboard:

#### 1. PostgreSQL Database
- **Name**: `manic-ai-db`
- **Database**: `manic_ai`
- **User**: `manic_ai`
- **Plan**: Starter ($7/mo) or Free (90 days)
- Copy the **Internal Database URL** (you'll need this)

#### 2. Redis
- **Name**: `manic-ai-redis`
- **Plan**: Starter ($10/mo) or Free (90 days)
- Copy the **Internal Redis URL** (you'll need this)

#### 3. Web Service (API)
- **Name**: `manic-ai-api`
- **Type**: Web Service
- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Plan**: Starter ($7/mo) or Free (750 hours/mo)

#### 4. Background Worker (Celery)
- **Name**: `manic-ai-worker`
- **Type**: Background Worker
- **Environment**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `celery -A app.worker.celery_app worker --loglevel=info --concurrency=2`
- **Plan**: Starter ($7/mo) or Free (750 hours/mo)

## Step 2: Set Environment Variables

### For Web Service (manic-ai-api)

Go to **Environment** tab and add:

```bash
# Required: Database (from Step 1.1)
DATABASE_URL=postgresql://manic_ai:xxxxx@manic-ai-db:5432/manic_ai

# Required: Redis (from Step 1.2)
REDIS_URL=redis://manic-ai-redis:6379

# Required: LLM Provider
LLM_PROVIDER=groq
LLM_API_KEY=your_groq_api_key_here
LLM_MODEL=llama-3.3-70b-versatile

# Required: Security
TOKEN_ENCRYPTION_KEY=generate_this_with_python_command_below
ADMIN_SECRET=choose_a_strong_secret

# Optional: DigiMarkIn JWT (for production)
DIGIMARKIN_JWKS_URL=
DIGIMARKIN_JWT_ISSUER=
DIGIMARKIN_JWT_AUDIENCE=

# Optional: GitHub OAuth (for coding tasks)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=
```

### For Background Worker (manic-ai-worker)

Add the **same environment variables** as the web service (except `ADMIN_SECRET` is optional).

## Step 3: Generate TOKEN_ENCRYPTION_KEY

Run this locally:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and paste it into `TOKEN_ENCRYPTION_KEY` for both services.

## Step 4: Deploy

1. Click **"Manual Deploy"** → **"Deploy latest commit"** for both services
2. Wait for builds to complete (~2-3 minutes)
3. Check logs for any errors

## Step 5: Verify Deployment

### Test Health Endpoint
```bash
curl https://manic-ai-api.onrender.com/health
```

Expected response:
```json
{"status":"ok","service":"manic-ai-orchestrator"}
```

### Test Task Creation (Development Mode)
```bash
curl -X POST https://manic-ai-api.onrender.com/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "test-org",
    "prompt": "Research AI trends for 2024"
  }'
```

Note: In development mode (no JWT configured), all requests use a test user ID.

## Step 6: Check Logs

### Web Service Logs
```bash
# In Render dashboard: Logs tab for manic-ai-api
# Or via CLI:
render logs manic-ai-api
```

### Worker Logs
```bash
# In Render dashboard: Logs tab for manic-ai-worker
# Or via CLI:
render logs manic-ai-worker
```

Look for:
- ✅ "Application startup complete"
- ✅ "Uvicorn running on http://0.0.0.0:PORT"
- ❌ Any Python tracebacks

## Troubleshooting

### Error: "Field required" for environment variables
**Solution**: You missed setting some env vars. Go back to Step 2 and add all required variables.

### Error: "Connection refused" to database
**Solution**: 
1. Check `DATABASE_URL` is the **Internal Database URL** (not external)
2. Ensure database is in the same region as web service
3. Wait 1-2 minutes for database to be ready after creation

### Error: "Connection refused" to Redis
**Solution**:
1. Check `REDIS_URL` is the **Internal Redis URL**
2. Ensure Redis is in the same region as web service

### Error: "LLM call failed"
**Solution**:
1. Verify `LLM_API_KEY` is correct
2. Check Groq account has credits (free tier gives $1/month)
3. Test API key locally: `curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer YOUR_KEY"`

### Worker not processing tasks
**Solution**:
1. Check worker logs for errors
2. Verify `REDIS_URL` is the same for both API and worker
3. Check task status via API: `GET /tasks/{task_id}`

### Task stuck in "running" forever
**Solution**:
1. Check worker logs — is it actually processing?
2. Check for LLM API errors (rate limits, invalid key)
3. Check database connectivity
4. Task timeout is 30 minutes by default — it will auto-fail

## Cost Optimization

### Free Tier Strategy
- Use Render free tier for testing (90 days for DB/Redis, 750 hours/mo for services)
- Use Groq free tier ($1/month credit)
- Set `MAX_LLM_CALLS_PER_TASK=10` to limit costs
- Use smaller models: `LLM_MODEL=llama-3.2-3b-versatile` (cheaper)

### Production Costs (Estimated)
- Render Starter plan: $7/mo (API) + $7/mo (worker) + $7/mo (DB) + $10/mo (Redis) = **$31/mo**
- Groq API: ~$0.20 per 1M tokens (very cheap)
- Total: **~$35-50/mo** for light usage

## Production Checklist

Before going live:

- [ ] Set `DIGIMARKIN_JWKS_URL` and JWT settings (for real auth)
- [ ] Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` (for coding tasks)
- [ ] Generate strong `ADMIN_SECRET`
- [ ] Set `ADMIN_ALLOWED_IPS` to restrict admin endpoints
- [ ] Configure `RATE_LIMIT_TASKS_PER_MINUTE` (default: 10)
- [ ] Set `TASK_TIMEOUT_MINUTES` (default: 30)
- [ ] Enable monitoring/alerts in Render dashboard
- [ ] Set up backups for PostgreSQL database
- [ ] Configure custom domain (optional)
- [ ] Set up SSL certificate (automatic with Render)

## Connecting to Your VPS Qwen

If you want to use your self-hosted Qwen on VPS (200.141.1.1) instead of Groq:

1. **Expose Ollama on VPS**:
   ```bash
   # On VPS: Edit Ollama service
   sudo systemctl edit ollama
   ```
   
   Add:
   ```ini
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```
   
   Restart:
   ```bash
   sudo systemctl restart ollama
   ```

2. **Test from VPS**:
   ```bash
   curl http://localhost:11434/v1/models
   ```

3. **Set in Render**:
   ```bash
   LLM_PROVIDER=local
   LLM_BASE_URL=http://200.141.1.1:11434/v1
   LLM_MODEL=qwen2.5:3b
   LLM_API_KEY=  # leave empty
   ```

4. **Allow VPS to accept external connections**:
   - Configure firewall to allow port 11434
   - Or use a reverse proxy with authentication

## Next Steps

1. ✅ Deploy to Render
2. ✅ Test with simple tasks (no coding)
3. ✅ Verify LLM calls work
4. ⏳ Set up DigiMarkIn JWT integration
5. ⏳ Configure GitHub OAuth for coding tasks
6. ⏳ Build frontend integration in DigiMarkIn

## Support

- Render docs: https://render.com/docs
- Groq docs: https://console.groq.com/docs
- This project: https://github.com/NavinReddy91/manic-ai-orchestrator

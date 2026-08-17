# Quick Start: Deploy Manic AI Orchestrator

This guide covers both **Render** (cloud) and **Hostinger VPS** (self-hosted) deployment.

## What Was Fixed

✅ **Render Error Fixed**: All environment variables are now optional with sensible defaults
✅ **YAML Warning Fixed**: Removed deprecated `version` field from docker-compose.yml
✅ **Local Model Support**: Added support for self-hosted Qwen via Ollama
✅ **Development Mode**: App can start without full configuration for testing

---

## Option 1: Render Deployment (Easiest)

### Step 1: Fork/Use the Repo
Repo: https://github.com/NavinReddy91/manic-ai-orchestrator

### Step 2: Deploy on Render

#### Quick Method (Blueprint)
1. Go to https://dashboard.render.com/blueprints
2. Click "New Blueprint Instance"
3. Connect repo: `NavinReddy91/manic-ai-orchestrator`
4. Render auto-detects `render.yaml` and creates all services
5. Set environment variables (see below)
6. Click "Apply"

#### Manual Method
Create these services in Render:
1. **PostgreSQL Database** (Starter plan: $7/mo or Free for 90 days)
2. **Redis** (Starter plan: $10/mo or Free for 90 days)
3. **Web Service** (API - Starter plan: $7/mo or Free)
4. **Background Worker** (Celery - Starter plan: $7/mo or Free)

### Step 3: Set Environment Variables

**Minimum Required:**
```bash
DATABASE_URL=postgresql://...  # From Render database
REDIS_URL=redis://...          # From Render Redis
LLM_PROVIDER=groq
LLM_API_KEY=your_groq_key      # Get from https://console.groq.com
LLM_MODEL=llama-3.3-70b-versatile
TOKEN_ENCRYPTION_KEY=          # Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**Optional (add later):**
```bash
DIGIMARKIN_JWKS_URL=           # For JWT auth (optional for testing)
GITHUB_CLIENT_ID=              # For coding tasks (optional)
GITHUB_CLIENT_SECRET=          # For coding tasks (optional)
ADMIN_SECRET=                  # For admin endpoints (optional)
```

### Step 4: Test
```bash
curl https://your-app.onrender.com/health
# Should return: {"status":"ok","service":"manic-ai-orchestrator"}
```

### Step 5: Create Test Task
```bash
curl -X POST https://your-app.onrender.com/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "test-org",
    "prompt": "Research AI trends for 2024"
  }'
```

**Full Guide**: See `RENDER_DEPLOYMENT.md`

---

## Option 2: Hostinger VPS Deployment (Self-Hosted)

### Step 1: SSH into VPS
```bash
ssh root@200.141.1.1  # or your VPS IP
```

### Step 2: Clone Repo
```bash
cd /docker  # or wherever you want to deploy
git clone https://github.com/NavinReddy91/manic-ai-orchestrator.git
cd manic-ai-orchestrator
```

### Step 3: Create .env File
```bash
cp .env.example .env
nano .env
```

**Fill in:**
```bash
# Infrastructure
POSTGRES_PASSWORD=your-secure-password
DATABASE_URL=postgresql://nexus:your-secure-password@postgres:5432/nexus_orchestrator
REDIS_URL=redis://redis:6379/0

# LLM - Use your existing Qwen
LLM_PROVIDER=local
LLM_API_KEY=
LLM_MODEL=qwen2.5:3b
LLM_BASE_URL=http://host.docker.internal:11434/v1

# Security
TOKEN_ENCRYPTION_KEY=  # Generate: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ADMIN_SECRET=your-admin-secret

# Optional (add later)
DIGIMARKIN_JWKS_URL=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

### Step 4: Update docker-compose.yml
Add `extra_hosts` to allow containers to access host network:

```yaml
services:
  api:
    # ... existing config ...
    extra_hosts:
      - "host.docker.internal:host-gateway"

  worker:
    # ... existing config ...
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### Step 5: Deploy via Hostinger Docker Manager
1. Go to Hostinger VPS Control Panel
2. Click "Docker Manager"
3. Project URL: `https://github.com/NavinReddy91/manic-ai-orchestrator`
4. Click "Deploy"

### Step 6: Verify Qwen is Accessible
```bash
# Test from VPS host
curl http://localhost:11434/v1/models

# Test from inside container
docker exec -it manic-ai-orchestrator-api-1 curl http://host.docker.internal:11434/v1/models
```

### Step 7: Test the App
```bash
curl http://localhost:8010/health
# Should return: {"status":"ok","service":"manic-ai-orchestrator"}
```

---

## Connecting Your Existing Qwen (200.141.1.1)

If Qwen is already running on your VPS:

### Step 1: Ensure Ollama is Running
```bash
# Check if Ollama is running
systemctl status ollama

# If not running, start it
sudo systemctl start ollama
```

### Step 2: Configure Ollama to Accept External Connections
```bash
# Edit Ollama service
sudo systemctl edit ollama
```

Add:
```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

Restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Step 3: Test Ollama
```bash
curl http://localhost:11434/v1/models
# Should list your Qwen model
```

### Step 4: Configure Manic AI
In `.env` (for VPS) or Render Environment Variables:
```bash
LLM_PROVIDER=local
LLM_BASE_URL=http://200.141.1.1:11434/v1  # Your VPS IP
LLM_MODEL=qwen2.5:3b
LLM_API_KEY=  # Leave empty for local
```

### Step 5: Firewall (if needed)
```bash
# Allow port 11434
sudo ufw allow 11434/tcp
```

---

## Troubleshooting

### Render: "Field required" errors
✅ **Fixed**: All fields now have defaults. Pull latest code and redeploy.

### Render: Database connection refused
- Use **Internal Database URL** (not external)
- Ensure database is in same region as web service

### VPS: YAML parsing error
✅ **Fixed**: Pulled latest code (removed `version` field)

### VPS: Can't connect to Qwen
- Check Ollama is running: `systemctl status ollama`
- Check Ollama is listening: `netstat -tlnp | grep 11434`
- Test from container: `docker exec -it api-container curl http://host.docker.internal:11434/v1/models`

### Qwen 2.5 3B Limitations
- Small model (3B parameters) may struggle with complex multi-agent tasks
- May produce invalid JSON (agents need valid JSON)
- **Recommendation**: Test with simple tasks first, use larger model (7B+) or cloud API for production

---

## Cost Comparison

| Option | Monthly Cost | Pros | Cons |
|--------|--------------|------|------|
| **Render Free Tier** | $0 (90 days) | Easy setup, managed | Limited after 90 days |
| **Render Starter** | ~$31/mo | Reliable, managed | More expensive |
| **Hostinger VPS** | $0 extra (if you already have it) | Full control, use existing Qwen | More setup, you manage |
| **New VPS** | $5-12/mo | Full control | You manage everything |

---

## Next Steps

1. ✅ Choose deployment option (Render or VPS)
2. ✅ Deploy with minimal config
3. ✅ Test health endpoint
4. ✅ Create test task (non-coding)
5. ⏳ Test with coding task (requires GitHub OAuth)
6. ⏳ Integrate with DigiMarkIn frontend
7. ⏳ Configure JWT auth for production

---

## Quick Commands

### Generate Encryption Key
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Test Health
```bash
curl http://localhost:8010/health
```

### Create Test Task
```bash
curl -X POST http://localhost:8010/tasks \
  -H "Content-Type: application/json" \
  -d '{"organization_id":"test","prompt":"Research AI trends"}'
```

### Check Task Status
```bash
curl http://localhost:8010/tasks/{task_id}
```

### View Logs (VPS)
```bash
docker logs manic-ai-orchestrator-api-1 -f
docker logs manic-ai-orchestrator-worker-1 -f
```

---

## Support

- **Render Guide**: `RENDER_DEPLOYMENT.md`
- **Full Documentation**: `README.md`
- **GitHub Repo**: https://github.com/NavinReddy91/manic-ai-orchestrator

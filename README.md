# Manic AI Orchestrator

**The Intelligent Multi-Agent Platform for Autonomous Business Operations**

Manic AI is a revolutionary hierarchical multi-agent system where AI agents work together like a real company. A Chief Agent orchestrates department heads (Engineering, Marketing, Growth, Finance, Sales, Operations), each managing specialized teams that collaborate, review each other's work, and deliver comprehensive solutions.

Unlike simple chatbots or single-agent systems, Manic AI creates an entire AI workforce that thinks, plans, executes, and quality-checks — autonomously.

## 🚀 What Makes Manic AI Unique

### 🏢 Real Organizational Structure
Most AI tools are single agents trying to do everything. Manic AI builds **entire AI companies**:
- **Chief Agent** (CEO) — Strategic planning and delegation
- **6 Department Heads** — Specialized management
- **10+ Specialist Agents** — Deep expertise in their domains
- **Quality Assurance** — Built-in review and revision cycles

### 🔄 Hierarchical Intelligence
```
User Request → Chief Agent (Strategic Planning)
                    ↓
        ┌───────────┼───────────┬───────────┬──────────┬──────────┐
        ↓           ↓           ↓           ↓          ↓          ↓
   Engineering  Marketing    Growth     Finance    Sales     Operations
   (5 agents)   (2 agents)  (2 agents) (1 agent)  (1 agent)  (1 agent)
        ↓           ↓           ↓           ↓          ↓          ↓
   [Review]     [Review]    [Review]   [Review]   [Review]   [Review]
        ↓           ↓           ↓           ↓          ↓          ↓
        └───────────┴───────────┴───────────┴──────────┴──────────┘
                              ↓
                    Chief Agent (Final Report)
```

### ✨ Key Differentiators

1. **Multi-Agent Collaboration** — Agents don't work in isolation; they coordinate, review, and refine each other's work
2. **Quality Assurance Built-In** — Every department head reviews their team's output before reporting up
3. **Revision Cycles** — Work gets sent back for improvements (up to 2 revisions per agent)
4. **Live Web Research** — Agents can search the web and fetch real-time data
5. **Real Code Execution** — Engineering team can clone repos, write code, test, and open PRs
6. **Organization Boundaries** — Hard isolation between different businesses/projects
7. **Cost Control** — Track LLM usage and set limits per task
8. **Webhook Integration** — Get notified when tasks complete

## 🎯 Use Cases

### For Businesses
- **Market Research** — "Analyze our top 5 competitors and identify market gaps"
- **Content Strategy** — "Create a 3-month content calendar for our SaaS product"
- **Financial Analysis** — "Review our Q4 expenses and suggest cost optimizations"
- **Sales Outreach** — "Draft personalized emails for 10 high-value prospects"
- **Operations Planning** — "Create a vendor management system for our supply chain"

### For Developers
- **Code Reviews** — "Review this PR for security vulnerabilities and performance issues"
- **Feature Development** — "Implement user authentication with OAuth2"
- **Bug Fixing** — "Debug this memory leak in our Node.js application"
- **Documentation** — "Generate API documentation from our codebase"
- **Testing** — "Write unit tests for our payment processing module"

### For Marketers
- **Campaign Planning** — "Design a product launch campaign across social media"
- **SEO Analysis** — "Audit our website and suggest SEO improvements"
- **Content Creation** — "Write blog posts, social media content, and email newsletters"
- **Competitor Analysis** — "Research competitor pricing and positioning"

## 🚀 Quick Start

### Deploy to Render (2 Minutes)

1. **Get API Key** — Sign up at https://console.groq.com (free tier)

2. **Deploy on Render**:
   - Go to https://dashboard.render.com
   - Click "New +" → "Blueprint"
   - Connect: `NavinReddy91/manic-ai-orchestrator`
   - Set environment variable: `LLM_API_KEY=your_groq_key`
   - Click "Apply"

3. **Test It**:
   ```bash
   curl https://your-app.onrender.com/health
   # Returns: {"status":"ok","service":"manic-ai-orchestrator"}
   ```

### Local Development

```bash
# Clone
git clone https://github.com/NavinReddy91/manic-ai-orchestrator.git
cd manic-ai-orchestrator

# Configure
cp .env.example .env
# Edit .env and add your LLM_API_KEY

# Run with Docker
docker compose up -d

# Or run manually
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
celery -A app.worker.celery_app worker --loglevel=info
```

## 🤖 How It Works

### 1. You Submit a Task
```bash
POST /tasks
{
  "organization_id": "my-business",
  "prompt": "Research AI trends and create a strategy document"
}
```

### 2. Chief Agent Plans
The Chief Agent analyzes your request and decides which departments are needed:
- Simple marketing task? → Marketing team only
- Code feature? → Engineering team
- Business strategy? → Growth + Marketing + Finance

### 3. Departments Execute
Each department head:
- Breaks down the work for their specialists
- Specialists execute (with live web access if needed)
- Department head reviews the work
- Sends back for revisions if needed (up to 2 rounds)
- Reports final results to Chief Agent

### 4. Chief Agent Compiles
The Chief Agent:
- Reviews all department outputs
- Compiles a comprehensive final report
- Delivers the complete solution

### 5. You Get Results
```bash
GET /tasks/{task_id}
{
  "status": "done",
  "final_report": "Comprehensive strategy document...",
  "org_tree": {
    "agent_key": "ceo",
    "status": "done",
    "children": [
      {
        "agent_key": "marketing_head",
        "status": "done",
        "children": [...]
      }
    ]
  }
}
```

## 🏗️ The Agent Hierarchy

### Engineering Department (5 Agents)
- **Engineering Manager** — Coordinates the team
- **Frontend Developer** — UI/UX implementation
- **Backend Developer** — Server-side logic
- **Frontend QA** — Reviews frontend code
- **Backend QA** — Reviews backend code
- **Integration Tester** — End-to-end testing

**Special Feature**: Sequential execution with real git operations
- Clones your repository
- Creates feature branches
- Writes and tests code
- Commits and pushes
- Opens pull requests

### Marketing Department (2 Agents)
- **Marketing Manager** — Strategy and coordination
- **Content Specialist** — Creates marketing content
- **Growth Marketer** — SEO, ads, analytics

### Growth Department (2 Agents)
- **Growth Manager** — Business development
- **Market Researcher** — Competitive analysis
- **Business Analyst** — Strategic planning

### Finance Department (1 Agent)
- **Finance Manager** — Financial analysis and planning

### Sales Department (1 Agent)
- **Sales Manager** — Sales strategy and outreach

### Operations Department (1 Agent)
- **Operations Manager** — Process optimization

## 🎨 What Makes It Special

### 1. **Real Collaboration, Not Just Parallel Execution**
Agents don't just work side-by-side — they actually review and improve each other's work. The Marketing Manager doesn't just pass through the Content Specialist's work; they critique it, request changes, and ensure quality.

### 2. **Hierarchical Decision Making**
The Chief Agent doesn't just delegate — it makes strategic decisions about which teams are needed, reviews final outputs, and ensures coherence across departments.

### 3. **Built-In Quality Assurance**
Every department has a review cycle. Work isn't considered done until the manager approves it. This catches errors and improves quality automatically.

### 4. **Live Web Access**
Agents can search the web and fetch real-time data. Need current market prices? Competitor analysis? Latest trends? Agents can research it themselves.

### 5. **Real Code Execution**
The Engineering team doesn't just suggest code — they actually write it, test it, and create pull requests in your repository.

### 6. **Organization Isolation**
Run multiple businesses on the same instance. Each organization has its own:
- Tasks and history
- Connected accounts (GitHub, etc.)
- Agent configurations
- Complete data isolation

### 7. **Cost Transparency**
Track exactly how many LLM calls each task makes and estimate token usage. Set limits to control costs.

### 8. **Webhook Integration**
Don't poll for results — get notified via webhook when tasks complete. Perfect for integration with other systems.

## 🔧 Configuration

### LLM Providers
Manic AI works with any major LLM provider:

```bash
# Groq (Recommended - Fast & Free Tier)
LLM_PROVIDER=groq
LLM_API_KEY=gsk_xxxxx
LLM_MODEL=llama-3.3-70b-versatile

# Google Gemini (Free Tier)
LLM_PROVIDER=gemini
LLM_API_KEY=AIxxxxx
LLM_MODEL=gemini-2.0-flash

# OpenAI (GPT-4)
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxxxx
LLM_MODEL=gpt-4o

# Anthropic (Claude)
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-xxxxx
LLM_MODEL=claude-sonnet-4-6

# Local (Ollama - Free, Private)
LLM_PROVIDER=local
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
```

### Authentication
```bash
# No auth (testing)
API_KEY=

# API key auth (production)
API_KEY=your-secret-key
```

### Optional Features
```bash
# GitHub integration (for coding tasks)
GITHUB_CLIENT_ID=xxxxx
GITHUB_CLIENT_SECRET=xxxxx

# Admin endpoints
ADMIN_SECRET=your-admin-secret

# Cost control
MAX_LLM_CALLS_PER_TASK=50
```

## 📡 API Examples

### Create a Task
```bash
curl -X POST https://manic-ai.com/tasks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "organization_id": "my-business",
    "prompt": "Analyze our competitors and create a positioning strategy"
  }'
```

### Check Task Status
```bash
curl https://manic-ai.com/tasks/task-123 \
  -H "X-API-Key: your-key"
```

### Cancel a Task
```bash
curl -X DELETE https://manic-ai.com/tasks/task-123 \
  -H "X-API-Key: your-key"
```

### Create Task with Webhook
```bash
curl -X POST https://manic-ai.com/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "my-business",
    "prompt": "Research market trends",
    "callback_url": "https://your-app.com/webhook"
  }'
```

## 🎯 Advanced Features

### Task Templates
Save common prompts for reuse:
```bash
POST /task-templates
{
  "name": "Competitor Analysis",
  "prompt": "Analyze top 5 competitors in [industry] and identify opportunities",
  "description": "Standard competitor analysis template"
}
```

### Organization-Specific Agent Customization
Customize agent behavior per organization:
```bash
POST /org-agent-overrides
{
  "organization_id": "my-business",
  "agent_key": "marketing_head",
  "system_prompt_override": "You are a B2B SaaS marketing expert..."
}
```

### Priority Tasks
Mark urgent tasks:
```bash
POST /tasks
{
  "organization_id": "my-business",
  "prompt": "Critical security issue - patch immediately",
  "priority": 2  # 0=normal, 1=high, 2=urgent
}
```

## 📊 Monitoring & Admin

### View All Tasks
```bash
GET /admin/tasks?status=running
```

### System Statistics
```bash
GET /admin/stats
{
  "total_tasks": 1234,
  "tasks_by_status": {"done": 1000, "running": 50, "failed": 24},
  "total_llm_calls": 5678,
  "total_estimated_tokens": 1234567
}
```

### Audit Logs
```bash
GET /admin/audit?user_id=user-123
```

## 🔒 Security & Privacy

### Organization Boundaries
- Each organization is completely isolated
- No cross-organization data access
- Separate task histories
- Independent connected accounts

### Authentication
- API key authentication (or no auth for testing)
- Optional admin endpoints with separate secret
- Rate limiting to prevent abuse

### Data Protection
- GitHub tokens encrypted at rest (Fernet encryption)
- No data shared between organizations
- Audit logging for all actions

## 💰 Pricing & Costs

### Self-Hosted (Your Infrastructure)
- **Render Free Tier**: $0 (90 days), then ~$17/month
- **VPS**: $5-20/month (depending on provider)
- **LLM Costs**: $0.01-0.10 per task (depending on complexity)

### LLM Provider Costs
- **Groq**: Free tier available, then $0.20 per 1M tokens
- **Gemini**: Free tier available, then pay-per-use
- **OpenAI/Anthropic**: Pay-per-use
- **Local (Ollama)**: $0 (your hardware)

### Typical Task Costs
- Simple research task: ~$0.01-0.02
- Marketing strategy: ~$0.05-0.10
- Code feature (with PR): ~$0.10-0.20

## 🚀 Deployment Options

### 1. Render (Easiest)
- One-click deploy from GitHub
- Free tier available
- Automatic HTTPS
- Managed infrastructure

### 2. Docker Compose (VPS)
- Full control
- Use your own server
- Connect to local LLM (Ollama)

### 3. Kubernetes (Enterprise)
- Scale horizontally
- High availability
- Production-grade

## 📚 Documentation

- **Deployment Guide**: `DEPLOYMENT.md`
- **API Documentation**: Available at `/docs` endpoint
- **Architecture**: See agent hierarchy above
- **Examples**: Check use cases section

## 🎓 Getting Started Checklist

1. ✅ Deploy to Render or local Docker
2. ✅ Get LLM API key (Groq recommended for testing)
3. ✅ Create your first organization
4. ✅ Submit a simple task (research, content)
5. ✅ Review the agent hierarchy in the response
6. ✅ Try a coding task (requires GitHub integration)
7. ✅ Set up webhooks for real-time notifications
8. ✅ Customize agents for your use case

## 🌟 Why Manic AI?

### vs. ChatGPT / Claude
- **ChatGPT**: Single agent, no collaboration, no quality checks
- **Manic AI**: Entire AI company, hierarchical review, built-in QA

### vs. AutoGPT / BabyAGI
- **AutoGPT**: Single agent with tools, no organizational structure
- **Manic AI**: Multi-agent hierarchy with real collaboration

### vs. LangChain Agents
- **LangChain**: Framework for building agents, not a complete solution
- **Manic AI**: Production-ready multi-agent platform out of the box

### vs. Custom Agent Systems
- **Custom**: Months of development, maintenance burden
- **Manic AI**: Deploy in 2 minutes, production-ready

## 🔮 What's Next?

### Roadmap
- [ ] Custom agent roles (define your own specialists)
- [ ] Agent memory (long-term context across tasks)
- [ ] Multi-modal agents (image analysis, generation)
- [ ] Agent marketplace (share/reuse agent configurations)
- [ ] Advanced analytics (cost per department, success rates)
- [ ] Team collaboration (multiple users per organization)

## 🤝 Contributing

Manic AI is open source! Contributions welcome:
- Bug reports
- Feature requests
- Pull requests
- Documentation improvements

## 📄 License

MIT License - Free for commercial and personal use

## 🆘 Support

- **Documentation**: `DEPLOYMENT.md`, `/docs` endpoint
- **Issues**: https://github.com/NavinReddy91/manic-ai-orchestrator/issues
- **Discussions**: https://github.com/NavinReddy91/manic-ai-orchestrator/discussions

---

## 🎉 Ready to Transform Your Business?

Manic AI isn't just another AI tool — it's an **AI workforce** that works for you.

**Deploy now and see the difference:**
```bash
# 2-minute deploy to Render
https://dashboard.render.com/blueprints
```

**Questions?** Check `DEPLOYMENT.md` or open an issue on GitHub.

---

**Manic AI — Where AI Agents Work Together Like a Real Company** 🚀

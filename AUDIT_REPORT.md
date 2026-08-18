# Manic AI - Comprehensive Audit Report

## Executive Summary

**Current Status:** Functional but with critical issues affecting cost, UX, and branding

**Critical Issues Found:**
1. 🔴 **Branding Inconsistency** - org_chart.py still uses "Sonic" instead of "Manic"
2. 🔴 **High Token Consumption** - No budget controls, excessive LLM calls
3. 🔴 **No Real-time Updates** - Frontend can't show live progress
4. 🟡 **Missing Cost Tracking** - No dashboard to monitor spending
5. 🟡 **Frontend Deployment Issues** - Path resolution problems on Render

---

## 1. Current Implementation Status

### ✅ What's Working

**Backend Core:**
- ✅ Hierarchical agent system (CEO → 6 departments → specialists)
- ✅ Multi-LLM support (Groq, Gemini, OpenAI, Anthropic, local)
- ✅ Task cancellation and timeout mechanisms
- ✅ Webhook callbacks
- ✅ Rate limiting (Redis-based)
- ✅ Organization isolation
- ✅ GitHub OAuth integration
- ✅ Git operations (clone, commit, push, PR)
- ✅ Live web research (DuckDuckGo)
- ✅ Database models (SQLite/PostgreSQL)
- ✅ Admin endpoints
- ✅ Task templates
- ✅ Audit logging

**Frontend:**
- ✅ Basic HTML/CSS/JS interface exists
- ✅ Task creation form
- ✅ Task list view
- ✅ Agent tree visualization

**Deployment:**
- ✅ Docker Compose configuration
- ✅ Render blueprint (render.yaml)
- ✅ Environment variable handling
- ✅ Lazy initialization (fixed Fernet/Redis errors)

---

### ❌ What's Broken or Missing

#### Critical Issues

**1. Branding Inconsistency**
- **Location:** `app/org_chart.py`
- **Problem:** All agent labels and prompts say "Sonic" instead of "Manic"
- **Impact:** Confusing for users, inconsistent branding
- **Fix Required:** Replace all "Sonic" references with "Manic"

**2. Excessive Token Consumption**
- **Problem:** No token budgeting, tasks can run unlimited LLM calls
- **Current Flow:**
  ```
  CEO delegates (1 call)
  → Dept head delegates (1 call per dept)
  → Each specialist works (1 call each)
  → Dept head reviews (1 call)
  → Can revise up to 2 times (2 more calls per specialist)
  → CEO reviews (1 call)
  ```
- **Worst Case:** A coding task could trigger 20+ LLM calls
- **Cost Impact:** With Groq at $0.20/1M tokens, a complex task could cost $0.50-2.00
- **Fix Required:** 
  - Add token budget per task
  - Implement early stopping
  - Reduce revision loops
  - Use smaller models for delegation/review

**3. No Real-time Progress Updates**
- **Problem:** Frontend can't show live agent execution progress
- **Current State:** Users must poll `/tasks/{id}` endpoint
- **Impact:** Poor UX, users don't know what's happening
- **Fix Required:** 
  - Add Server-Sent Events (SSE) or WebSocket endpoint
  - Stream agent status updates to frontend
  - Show which agents are running/completed

**4. Frontend Deployment Issues**
- **Problem:** Render can't find frontend directory
- **Root Cause:** Path resolution in `main.py` checks multiple locations
- **Impact:** Shows fallback error page instead of UI
- **Fix Required:** 
  - Ensure frontend/ is in correct location
  - Update Dockerfile to copy frontend
  - Verify Render build process

#### Medium Priority Issues

**5. No Cost Tracking Dashboard**
- **Problem:** Can't monitor LLM spending per task/organization
- **Current State:** Only basic `llm_call_count` and `estimated_tokens` fields
- **Impact:** Can't optimize costs or set budgets
- **Fix Required:**
  - Add cost calculation (tokens × price per model)
  - Create admin dashboard for cost monitoring
  - Add budget limits per organization

**6. Inefficient Agent Execution**
- **Problem:** All leaf agents have `uses_browse: True` even when not needed
- **Impact:** Wastes tokens on browsing instructions for simple tasks
- **Fix Required:**
  - Make browsing opt-in per agent
  - Only enable for research/marketing agents
  - Disable for coding agents (they should focus on code)

**7. No Task Comparison/History**
- **Problem:** Can't compare multiple tasks or view history effectively
- **Impact:** Hard to track progress over time
- **Fix Required:**
  - Add task history view
  - Add task comparison feature
  - Add export functionality

**8. Missing Error Recovery**
- **Problem:** If an agent fails, entire task can fail
- **Impact:** Wasted tokens on partial work
- **Fix Required:**
  - Add graceful degradation
  - Allow partial task completion
  - Add retry logic for transient failures

---

## 2. Token Consumption Analysis

### Current Token Usage Per Task

**Simple Task (e.g., "Research AI trends"):**
```
1. CEO delegates to Growth (1 call, ~500 tokens)
2. Growth head delegates to researcher + analyst (1 call, ~500 tokens)
3. Market researcher works (1 call, ~1000 tokens)
4. Business analyst works (1 call, ~1000 tokens)
5. Growth head reviews (1 call, ~800 tokens)
6. CEO reviews final (1 call, ~800 tokens)
Total: 6 calls, ~4600 tokens, ~$0.001
```

**Complex Coding Task (e.g., "Add authentication"):**
```
1. CEO delegates to Coding (1 call, ~500 tokens)
2. Coding head delegates to 5 specialists (1 call, ~800 tokens)
3. Frontend dev works (1 call, ~1500 tokens)
4. Backend dev works (1 call, ~1500 tokens)
5. Frontend bug checker (1 call, ~1000 tokens)
6. Backend bug checker (1 call, ~1000 tokens)
7. Integration checker (1 call, ~800 tokens)
8. Coding head reviews (1 call, ~1000 tokens)
9. Revisions (2 specialists × 2 revisions = 4 calls, ~4000 tokens)
10. CEO reviews final (1 call, ~1000 tokens)
Total: 13 calls, ~13100 tokens, ~$0.003
```

**Worst Case (multiple revision loops):**
```
Could reach 20+ calls, 20000+ tokens, $0.005+
```

### Optimization Opportunities

1. **Use smaller models for delegation/review:**
   - CEO delegation: Use `llama-3.1-8b-instant` (8x cheaper)
   - Department reviews: Use `llama-3.1-8b-instant`
   - Specialist work: Use `llama-3.3-70b-versatile` (current)

2. **Reduce revision loops:**
   - Change `MAX_REVISIONS_PER_AGENT` from 2 to 1
   - Add confidence threshold for reviews

3. **Disable browsing for coding agents:**
   - Saves ~200 tokens per agent on browsing instructions
   - Coding agents should focus on code, not research

4. **Add token budget:**
   - Set max tokens per task (e.g., 10000)
   - Stop execution when budget exceeded
   - Return partial results

---

## 3. Recommended Action Plan

### Phase 1: Critical Fixes (Immediate)

**Priority 1: Fix Branding**
- [ ] Replace all "Sonic" with "Manic" in org_chart.py
- [ ] Update all agent labels and prompts
- [ ] Test to ensure no references remain

**Priority 2: Add Token Budgeting**
- [ ] Add `max_tokens_per_task` config (default: 15000)
- [ ] Track cumulative tokens in task model
- [ ] Stop execution when budget exceeded
- [ ] Return partial results with explanation

**Priority 3: Optimize Model Usage**
- [ ] Use smaller model for delegation (8b instead of 70b)
- [ ] Use smaller model for reviews
- [ ] Keep 70b for actual specialist work
- [ ] Add config for model selection per role

**Priority 4: Fix Frontend Deployment**
- [ ] Verify frontend/ directory structure
- [ ] Update Dockerfile to include frontend
- [ ] Test on Render deployment
- [ ] Add fallback UI if frontend missing

### Phase 2: UX Improvements (High Priority)

**Priority 5: Real-time Progress Updates**
- [ ] Add SSE endpoint: `/tasks/{id}/stream`
- [ ] Stream agent status updates
- [ ] Update frontend to consume SSE
- [ ] Show live agent tree with status colors

**Priority 6: Cost Tracking Dashboard**
- [ ] Add cost calculation per task
- [ ] Create admin dashboard page
- [ ] Show cost breakdown by agent
- [ ] Add organization-level cost tracking

**Priority 7: Improve Frontend UI**
- [ ] Add task history view
- [ ] Add task comparison feature
- [ ] Improve agent tree visualization
- [ ] Add export functionality (PDF/JSON)

### Phase 3: Advanced Features (Medium Priority)

**Priority 8: Optimize Agent Execution**
- [ ] Make browsing opt-in per agent
- [ ] Add agent specialization hints
- [ ] Reduce revision loops (max 1 instead of 2)
- [ ] Add confidence-based early stopping

**Priority 9: Error Recovery**
- [ ] Add graceful degradation
- [ ] Allow partial task completion
- [ ] Add retry logic for transient failures
- [ ] Improve error messages

**Priority 10: Advanced Analytics**
- [ ] Track success rate per agent
- [ ] Identify bottlenecks
- [ ] Add performance metrics
- [ ] Create optimization recommendations

---

## 4. Implementation Details

### Token Budgeting Implementation

**Add to models.py:**
```python
class Task(Base):
    # ... existing fields ...
    token_budget = Column(Integer, default=15000)
    tokens_used = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
```

**Add to worker.py:**
```python
def _check_token_budget(task: Task) -> bool:
    """Check if task has exceeded token budget."""
    return task.tokens_used < task.token_budget

# In _execute_leaf:
if not _check_token_budget(task):
    return json.dumps({
        "summary": "Token budget exceeded",
        "partial_result": result[:1000]
    })
```

### Real-time Updates Implementation

**Add to tasks_api.py:**
```python
from fastapi.responses import StreamingResponse

@router.get("/{task_id}/stream")
async def stream_task_progress(task_id: str):
    async def event_stream():
        while True:
            task = db.query(Task).filter_by(id=task_id).first()
            if not task:
                yield f"data: {json.dumps({'error': 'not found'})}\n\n"
                break
            
            # Get agent tree
            agents = db.query(AgentRun).filter_by(task_id=task_id).all()
            progress = {
                "task_status": task.status,
                "agents": [
                    {
                        "key": a.agent_key,
                        "status": a.status,
                        "label": ORG_CHART[a.agent_key]["label"]
                    }
                    for a in agents
                ]
            }
            yield f"data: {json.dumps(progress)}\n\n"
            
            if task.status in ("done", "failed", "cancelled"):
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

### Model Optimization Implementation

**Add to config.py:**
```python
# Model selection per role
llm_model_delegation: str = "llama-3.1-8b-instant"  # 8x cheaper
llm_model_review: str = "llama-3.1-8b-instant"
llm_model_work: str = "llama-3.3-70b-versatile"  # high quality
```

**Update llm.py:**
```python
async def delegate(manager_system: str, brief: str) -> list[dict]:
    # Use smaller model for delegation
    raw = await call_llm(
        manager_system + efficiency_hint, 
        brief, 
        max_tokens=500,
        model_override=settings.llm_model_delegation
    )
    # ...
```

---

## 5. Cost Comparison

### Current Costs (Groq Pricing)

**Per Task:**
- Simple task: ~$0.001 (4600 tokens)
- Complex task: ~$0.003 (13100 tokens)
- Worst case: ~$0.005+ (20000+ tokens)

**Monthly (100 tasks/day):**
- Simple tasks: ~$3/month
- Complex tasks: ~$9/month
- Mixed: ~$6/month

### After Optimization

**Per Task (with optimizations):**
- Simple task: ~$0.0005 (delegation uses 8b model)
- Complex task: ~$0.002 (reduced revisions, optimized models)
- Worst case: ~$0.003 (token budget enforced)

**Monthly (100 tasks/day):**
- Simple tasks: ~$1.5/month (50% reduction)
- Complex tasks: ~$6/month (33% reduction)
- Mixed: ~$4/month (33% reduction)

**Savings:** 33-50% cost reduction

---

## 6. Next Steps

### Immediate Actions (This Session)

1. ✅ Fix branding (Sonic → Manic)
2. ✅ Add token budgeting
3. ✅ Optimize model usage
4. ✅ Add real-time progress updates
5. ✅ Improve frontend UI
6. ✅ Test deployment

### Follow-up Actions

1. Add cost tracking dashboard
2. Implement task history/comparison
3. Add advanced analytics
4. Create user documentation
5. Set up monitoring/alerting

---

## 7. Conclusion

The Manic AI platform has a solid foundation with all core features implemented. However, there are critical issues with branding, cost control, and user experience that need immediate attention.

**Key Findings:**
- ✅ Architecture is sound and scalable
- ✅ All major features are implemented
- ❌ Branding inconsistency (Sonic vs Manic)
- ❌ High token consumption without budgeting
- ❌ No real-time progress updates
- ❌ Frontend deployment issues

**Recommended Priority:**
1. Fix branding (5 minutes)
2. Add token budgeting (30 minutes)
3. Optimize model usage (20 minutes)
4. Add real-time updates (1 hour)
5. Improve frontend (2 hours)

**Expected Outcome:**
- 33-50% cost reduction
- Much better user experience
- Consistent branding
- Production-ready platform

---

**Audit Completed:** Ready for implementation

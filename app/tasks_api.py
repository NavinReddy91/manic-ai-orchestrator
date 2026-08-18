"""
Manic AI — Tasks API
Create, list, get, and cancel tasks.
"""

import asyncio
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import get_current_user
from .db import get_db
from .models import Task, AgentRun, Organization
from .org_chart import ORG_CHART, ROOT_AGENT
from .background_worker import start_task_execution
from .rate_limiter import check_rate_limit
from .audit import log_action

router = APIRouter(prefix="/tasks", tags=["tasks"])
logger = logging.getLogger(__name__)


class CreateTaskRequest(BaseModel):
    organization_id: str
    prompt: str
    repo: str | None = None  # "owner/repo" — only needed if the request touches code
    callback_url: str | None = None  # webhook URL to POST when task completes
    priority: int = 0  # 0=normal, 1=high, 2=urgent
    token_budget: int | None = None  # Optional: override default token budget


@router.post("")
async def create_task(
    body: CreateTaskRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new task. Subject to rate limiting."""
    # Check rate limits
    check_rate_limit(user["sub"])

    # Verify org ownership
    org = (
        db.query(Organization)
        .filter_by(id=body.organization_id, user_id=user["sub"])
        .first()
    )
    if not org:
        raise HTTPException(
            status_code=404, detail="Organization not found for this user"
        )

    # Create task
    from .config import settings

    task = Task(
        user_id=user["sub"],
        organization_id=org.id,
        prompt=body.prompt,
        repo=body.repo,
        callback_url=body.callback_url,
        priority=body.priority,
        token_budget=body.token_budget or settings.max_tokens_per_task,
        status="planning",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Log the action
    client_ip = request.client.host if request.client else None
    log_action(
        db,
        user_id=user["sub"],
        action="task_created",
        organization_id=org.id,
        task_id=task.id,
        details={
            "prompt": body.prompt[:200],
            "repo": body.repo,
            "priority": body.priority,
        },
        ip_address=client_ip,
    )

    # Start task execution in background
    background_tasks.add_task(_run_task_background, task.id, user["sub"])

    logger.info(f"Task created: {task.id} for org {org.id}")

    return _serialize_task(db, task)


@router.get("/{task_id}")
def get_task(
    task_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a task with its full agent execution tree."""
    task = db.query(Task).filter_by(id=task_id, user_id=user["sub"]).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_task(db, task)


@router.get("")
def list_tasks(
    organization_id: str | None = None,
    status: str | None = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List tasks for the authenticated user, optionally filtered by org or status."""
    query = db.query(Task).filter_by(user_id=user["sub"])
    if organization_id:
        query = query.filter_by(organization_id=organization_id)
    if status:
        query = query.filter_by(status=status)
    tasks = query.order_by(Task.created_at.desc()).all()
    return [_serialize_task(db, t) for t in tasks]


@router.delete("/{task_id}")
def cancel_task(
    task_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel a running task. Marks the task and all pending/running agent runs as cancelled.
    Celery will stop processing new agent nodes for this task.
    """
    task = db.query(Task).filter_by(id=task_id, user_id=user["sub"]).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ("running", "planning"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task in status '{task.status}' — only running or planning tasks can be cancelled",
        )

    # Mark task as cancelled
    task.status = "cancelled"
    task.cancelled_at = datetime.utcnow()
    task.completed_at = datetime.utcnow()

    # Cancel all pending/running agent runs
    from sqlalchemy import update

    db.execute(
        update(AgentRun)
        .where(
            AgentRun.task_id == task.id,
            AgentRun.status.in_(
                ["pending", "running", "awaiting_children", "reviewing"]
            ),
        )
        .values(status="cancelled", completed_at=datetime.utcnow())
    )

    db.commit()

    # Log the action
    client_ip = request.client.host if request.client else None
    log_action(
        db,
        user_id=user["sub"],
        action="task_cancelled",
        organization_id=task.organization_id,
        task_id=task.id,
        details={"status": task.status},
        ip_address=client_ip,
    )

    logger.info(f"Task cancelled: {task.id}")

    return {"status": "cancelled", "task_id": task.id}


@router.get("/{task_id}/stream")
async def stream_task_progress(
    task_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Server-Sent Events endpoint for real-time task progress updates.
    Streams agent status changes as they happen.
    """
    task = db.query(Task).filter_by(id=task_id, user_id=user["sub"]).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_stream():
        last_agent_states = {}

        while True:
            # Refresh task from DB
            db_task = db.query(Task).filter_by(id=task_id).first()
            if not db_task:
                yield f"data: {json.dumps({'error': 'Task not found'})}\n\n"
                break

            # Get all agent runs for this task
            agents = db.query(AgentRun).filter_by(task_id=task_id).all()

            # Build progress update
            agent_updates = []
            for agent in agents:
                current_state = {
                    "key": agent.agent_key,
                    "status": agent.status,
                    "label": ORG_CHART.get(agent.agent_key, {}).get(
                        "label", agent.agent_key
                    ),
                    "team": ORG_CHART.get(agent.agent_key, {}).get("team", "unknown"),
                }

                # Only send if state changed
                if last_agent_states.get(agent.id) != current_state:
                    agent_updates.append(current_state)
                    last_agent_states[agent.id] = current_state

            # Send update if there are changes or every 5 seconds as heartbeat
            if agent_updates or True:  # Always send for now (heartbeat)
                progress = {
                    "task_id": task_id,
                    "task_status": db_task.status,
                    "tokens_used": db_task.tokens_used,
                    "token_budget": db_task.token_budget,
                    "llm_call_count": db_task.llm_call_count,
                    "agents": agent_updates if agent_updates else None,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                yield f"data: {json.dumps(progress)}\n\n"

            # Check if task is complete
            if db_task.status in ("done", "failed", "cancelled"):
                # Send final update
                final_progress = {
                    "task_id": task_id,
                    "task_status": db_task.status,
                    "final_report": db_task.final_report,
                    "tokens_used": db_task.tokens_used,
                    "token_budget": db_task.token_budget,
                    "completed": True,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                yield f"data: {json.dumps(final_progress)}\n\n"
                break

            # Wait before next check
            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


def _serialize_node(db: Session, agent_run: AgentRun) -> dict:
    children = (
        db.query(AgentRun)
        .filter_by(parent_id=agent_run.id)
        .order_by(AgentRun.order_index)
        .all()
    )
    node = ORG_CHART[agent_run.agent_key]
    return {
        "id": agent_run.id,
        "agent_key": agent_run.agent_key,
        "label": node["label"],
        "team": node["team"],
        "status": agent_run.status,
        "instructions": agent_run.instructions,
        "result": agent_run.result,
        "revision_count": agent_run.revision_count,
        "started_at": agent_run.started_at.isoformat()
        if agent_run.started_at
        else None,
        "completed_at": agent_run.completed_at.isoformat()
        if agent_run.completed_at
        else None,
        "children": [_serialize_node(db, c) for c in children],
    }


def _serialize_task(db: Session, task: Task) -> dict:
    root = db.query(AgentRun).filter_by(task_id=task.id, parent_id=None).first()
    return {
        "id": task.id,
        "organization_id": task.organization_id,
        "prompt": task.prompt,
        "repo": task.repo,
        "branch": task.branch,
        "status": task.status,
        "final_report": task.final_report,
        "llm_call_count": task.llm_call_count,
        "estimated_tokens": task.estimated_tokens,
        "token_budget": task.token_budget,
        "tokens_used": task.tokens_used,
        "priority": task.priority,
        "callback_url": task.callback_url,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "cancelled_at": task.cancelled_at.isoformat() if task.cancelled_at else None,
        "org_tree": _serialize_node(db, root) if root else None,
    }


async def _run_task_background(task_id: str, user_id: str):
    """Wrapper to run the async task execution."""
    await start_task_execution(task_id, user_id)

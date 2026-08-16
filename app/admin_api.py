"""
Admin/debug endpoints — accessible without JWT, protected by admin_secret
or IP whitelist.
"""

import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from .config import settings
from .db import get_db
from .models import Task, AgentRun, Organization, AuditLog

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


def verify_admin_access(request: Request) -> None:
    """
    Verify admin access via Bearer token or IP whitelist.
    """
    # Check IP whitelist first (if configured)
    if settings.admin_allowed_ips:
        client_ip = request.client.host if request.client else None
        allowed_ips = [ip.strip() for ip in settings.admin_allowed_ips.split(",")]
        if client_ip and client_ip not in allowed_ips:
            raise HTTPException(status_code=403, detail="IP not allowed")
        if client_ip in allowed_ips:
            return  # IP is allowed, no token needed

    # Check Bearer token
    if not settings.admin_secret:
        raise HTTPException(status_code=403, detail="Admin access not configured")

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != settings.admin_secret:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/tasks")
def list_all_tasks(
    status: str | None = None,
    organization_id: str | None = None,
    limit: int = 100,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """List all tasks across all organizations (admin only)."""
    verify_admin_access(request)

    query = db.query(Task)
    if status:
        query = query.filter_by(status=status)
    if organization_id:
        query = query.filter_by(organization_id=organization_id)

    tasks = query.order_by(Task.created_at.desc()).limit(limit).all()
    return [
        {
            "id": t.id,
            "user_id": t.user_id,
            "organization_id": t.organization_id,
            "prompt": t.prompt[:200] + "..." if len(t.prompt) > 200 else t.prompt,
            "status": t.status,
            "llm_call_count": t.llm_call_count,
            "estimated_tokens": t.estimated_tokens,
            "priority": t.priority,
            "created_at": t.created_at.isoformat(),
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        }
        for t in tasks
    ]


@router.get("/tasks/stale")
def list_stale_tasks(
    minutes: int = 30,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """List tasks stuck in 'running' for longer than N minutes."""
    verify_admin_access(request)

    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    tasks = (
        db.query(Task).filter(Task.status == "running", Task.started_at < cutoff).all()
    )
    return [
        {
            "id": t.id,
            "user_id": t.user_id,
            "organization_id": t.organization_id,
            "prompt": t.prompt[:200],
            "started_at": t.started_at.isoformat(),
            "minutes_running": (datetime.utcnow() - t.started_at).total_seconds() / 60,
        }
        for t in tasks
    ]


@router.get("/stats")
def get_stats(request: Request = None, db: Session = Depends(get_db)):
    """Get system-wide statistics."""
    verify_admin_access(request)

    total_tasks = db.query(func.count(Task.id)).scalar()
    tasks_by_status = (
        db.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
    )
    total_llm_calls = db.query(func.sum(Task.llm_call_count)).scalar() or 0
    total_tokens = db.query(func.sum(Task.estimated_tokens)).scalar() or 0
    total_orgs = db.query(func.count(Organization.id)).scalar()

    return {
        "total_tasks": total_tasks,
        "tasks_by_status": {status: count for status, count in tasks_by_status},
        "total_llm_calls": total_llm_calls,
        "total_estimated_tokens": total_tokens,
        "total_organizations": total_orgs,
    }


@router.get("/audit")
def list_audit_logs(
    user_id: str | None = None,
    organization_id: str | None = None,
    task_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """List audit logs with optional filters."""
    verify_admin_access(request)

    query = db.query(AuditLog)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if organization_id:
        query = query.filter_by(organization_id=organization_id)
    if task_id:
        query = query.filter_by(task_id=task_id)
    if action:
        query = query.filter_by(action=action)

    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "organization_id": log.organization_id,
            "task_id": log.task_id,
            "action": log.action,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]

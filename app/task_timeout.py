"""
Background task to detect and fail stale tasks that have been running too long.
Runs as a Celery beat periodic task.
"""

import logging
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import Task, AgentRun

logger = logging.getLogger(__name__)


@shared_task(name="cleanup_stale_tasks")
def cleanup_stale_tasks():
    """
    Find tasks stuck in 'running' for longer than task_timeout_minutes and
    mark them as failed. Also cancels any pending/running agent runs for
    those tasks.
    """
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=settings.task_timeout_minutes)

        stale_tasks = (
            db.query(Task)
            .filter(
                Task.status == "running",
                Task.started_at < cutoff,
            )
            .all()
        )

        for task in stale_tasks:
            logger.warning(
                f"Task {task.id} has been running for over {settings.task_timeout_minutes} minutes — marking as failed"
            )

            # Cancel all pending/running agent runs
            stale_runs = (
                db.query(AgentRun)
                .filter(
                    AgentRun.task_id == task.id,
                    AgentRun.status.in_(
                        ["pending", "running", "awaiting_children", "reviewing"]
                    ),
                )
                .all()
            )
            for agent_run in stale_runs:
                agent_run.status = "cancelled"
                agent_run.completed_at = datetime.utcnow()

            # Mark task as failed
            task.status = "failed"
            task.final_report = (
                f"Task timed out after {settings.task_timeout_minutes} minutes"
            )
            task.completed_at = datetime.utcnow()

            db.commit()

        if stale_tasks:
            logger.info(f"Cleaned up {len(stale_tasks)} stale tasks")

    except Exception as e:
        logger.exception(f"Error in cleanup_stale_tasks: {e}")
        db.rollback()
    finally:
        db.close()

"""
Webhook callbacks — POST to a URL when a task completes.
"""

import logging
import httpx
from .models import Task

logger = logging.getLogger(__name__)


async def send_webhook(task: Task) -> None:
    """
    POST task result to the callback_url if set. Non-blocking — errors are
    logged but don't affect task status.
    """
    if not task.callback_url:
        return

    payload = {
        "task_id": task.id,
        "organization_id": task.organization_id,
        "status": task.status,
        "final_report": task.final_report,
        "repo": task.repo,
        "branch": task.branch,
        "llm_call_count": task.llm_call_count,
        "estimated_tokens": task.estimated_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(task.callback_url, json=payload)
            resp.raise_for_status()
            logger.info(f"Webhook sent for task {task.id}: {resp.status_code}")
    except Exception as e:
        logger.error(f"Webhook failed for task {task.id}: {e}")

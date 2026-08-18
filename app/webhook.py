"""
Webhook callbacks — POST to a URL when a task completes.
"""

import logging
from urllib.parse import urlparse
import httpx
from .models import Task

logger = logging.getLogger(__name__)

# Only allow HTTPS webhooks to public endpoints
_ALLOWED_SCHEMES = {"https"}


def _is_safe_webhook_url(url: str) -> bool:
    """Validate webhook URL is HTTPS and not targeting internal networks."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in _ALLOWED_SCHEMES:
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # Block common internal hostnames
        blocked = {
            "localhost",
            "127.0.0.1",
            "0.0.0.0",
            "::1",
            "metadata.google.internal",
        }
        if hostname.lower() in blocked:
            return False
        if hostname.startswith("169.254."):  # Cloud metadata
            return False
        return True
    except Exception:
        return False


async def send_webhook(task: Task) -> None:
    """
    POST task result to the callback_url if set. Non-blocking — errors are
    logged but don't affect task status.
    """
    if not task.callback_url:
        return

    if not _is_safe_webhook_url(task.callback_url):
        logger.warning(
            f"Webhook URL blocked for task {task.id}: {task.callback_url} "
            "(only HTTPS to public endpoints allowed)"
        )
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

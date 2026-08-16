"""
Audit logging for tracking important actions.
"""

import json
import logging
from sqlalchemy.orm import Session
from .models import AuditLog

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    user_id: str,
    action: str,
    organization_id: str | None = None,
    task_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """
    Log an audit event. Non-blocking — errors are logged but don't fail the request.
    """
    try:
        log_entry = AuditLog(
            user_id=user_id,
            organization_id=organization_id,
            task_id=task_id,
            action=action,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
        db.rollback()

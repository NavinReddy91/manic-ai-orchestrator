"""
Sonic AI — Organizations API
Create and list organizations.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import get_current_user
from .db import get_db
from .models import Organization
from .audit import log_action

router = APIRouter(prefix="/organizations", tags=["organizations"])
logger = logging.getLogger(__name__)


class CreateOrganizationRequest(BaseModel):
    name: str


def _serialize(org: Organization) -> dict:
    return {"id": org.id, "name": org.name, "created_at": org.created_at.isoformat()}


@router.post("")
def create_organization(
    body: CreateOrganizationRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new organization."""
    org = Organization(user_id=user["sub"], name=body.name)
    db.add(org)
    db.commit()
    db.refresh(org)

    # Log the action
    client_ip = request.client.host if request.client else None
    log_action(
        db,
        user_id=user["sub"],
        action="organization_created",
        organization_id=org.id,
        details={"name": body.name},
        ip_address=client_ip,
    )

    logger.info(f"Organization created: {org.id} ({body.name}) by user {user['sub']}")

    return _serialize(org)


@router.get("")
def list_organizations(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all organizations for the authenticated user."""
    orgs = (
        db.query(Organization)
        .filter_by(user_id=user["sub"])
        .order_by(Organization.created_at)
        .all()
    )
    return [_serialize(o) for o in orgs]

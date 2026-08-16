from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import get_current_user
from .db import get_db
from .models import Organization

router = APIRouter(prefix="/organizations", tags=["organizations"])


class CreateOrganizationRequest(BaseModel):
    name: str


def _serialize(org: Organization) -> dict:
    return {"id": org.id, "name": org.name, "created_at": org.created_at.isoformat()}


@router.post("")
def create_organization(
    body: CreateOrganizationRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = Organization(user_id=user["sub"], name=body.name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return _serialize(org)


@router.get("")
def list_organizations(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    orgs = db.query(Organization).filter_by(user_id=user["sub"]).order_by(Organization.created_at).all()
    return [_serialize(o) for o in orgs]

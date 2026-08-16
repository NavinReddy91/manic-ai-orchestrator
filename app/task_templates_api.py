"""
Task templates — saved prompts for reuse.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import get_current_user
from .db import get_db
from .models import TaskTemplate, Organization

router = APIRouter(prefix="/task-templates", tags=["task-templates"])


class CreateTemplateRequest(BaseModel):
    name: str
    prompt: str
    description: str | None = None
    organization_id: str | None = (
        None  # if set, template is org-specific; otherwise global for user
    )


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    prompt: str | None = None
    description: str | None = None


@router.post("")
def create_template(
    body: CreateTemplateRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new task template."""
    # Verify org ownership if org_id provided
    if body.organization_id:
        org = (
            db.query(Organization)
            .filter_by(id=body.organization_id, user_id=user["sub"])
            .first()
        )
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

    template = TaskTemplate(
        user_id=user["sub"],
        organization_id=body.organization_id,
        name=body.name,
        prompt=body.prompt,
        description=body.description,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return _serialize(template)


@router.get("")
def list_templates(
    organization_id: str | None = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List templates for the user (and optionally filtered by org)."""
    query = db.query(TaskTemplate).filter_by(user_id=user["sub"])
    if organization_id:
        query = query.filter(
            (TaskTemplate.organization_id == organization_id)
            | (TaskTemplate.organization_id == None)
        )
    templates = query.order_by(TaskTemplate.created_at.desc()).all()
    return [_serialize(t) for t in templates]


@router.get("/{template_id}")
def get_template(
    template_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific template."""
    template = (
        db.query(TaskTemplate).filter_by(id=template_id, user_id=user["sub"]).first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _serialize(template)


@router.put("/{template_id}")
def update_template(
    template_id: str,
    body: UpdateTemplateRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a template."""
    template = (
        db.query(TaskTemplate).filter_by(id=template_id, user_id=user["sub"]).first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if body.name is not None:
        template.name = body.name
    if body.prompt is not None:
        template.prompt = body.prompt
    if body.description is not None:
        template.description = body.description

    db.commit()
    db.refresh(template)
    return _serialize(template)


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a template."""
    template = (
        db.query(TaskTemplate).filter_by(id=template_id, user_id=user["sub"]).first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    db.delete(template)
    db.commit()
    return {"deleted": True}


def _serialize(template: TaskTemplate) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "prompt": template.prompt,
        "description": template.description,
        "organization_id": template.organization_id,
        "created_at": template.created_at.isoformat(),
    }

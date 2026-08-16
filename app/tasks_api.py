from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import get_current_user
from .db import get_db
from .models import Task, AgentRun, Organization
from .org_chart import ORG_CHART, ROOT_AGENT
from .worker import run_agent_node

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    organization_id: str
    prompt: str
    repo: str | None = None  # "owner/repo" — only needed if the request touches code


@router.post("")
async def create_task(
    body: CreateTaskRequest,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = (
        db.query(Organization)
        .filter_by(id=body.organization_id, user_id=user["sub"])
        .first()
    )
    if not org:
        raise HTTPException(
            status_code=404, detail="Organization not found for this user"
        )

    task = Task(
        user_id=user["sub"],
        organization_id=org.id,
        prompt=body.prompt,
        repo=body.repo,
        status="running",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    ceo_run = AgentRun(
        task_id=task.id,
        parent_id=None,
        agent_key=ROOT_AGENT,
        instructions=body.prompt,
        status="pending",
    )
    db.add(ceo_run)
    db.commit()
    db.refresh(ceo_run)

    run_agent_node.delay(ceo_run.id)  # fires the whole tree in the background from here

    return _serialize_task(db, task)


@router.get("/{task_id}")
def get_task(
    task_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    task = db.query(Task).filter_by(id=task_id, user_id=user["sub"]).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _serialize_task(db, task)


@router.get("")
def list_tasks(
    organization_id: str | None = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Task).filter_by(user_id=user["sub"])
    if organization_id:
        query = query.filter_by(organization_id=organization_id)
    tasks = query.order_by(Task.created_at.desc()).all()
    return [_serialize_task(db, t) for t in tasks]


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
        "created_at": task.created_at.isoformat(),
        "org_tree": _serialize_node(db, root) if root else None,
    }

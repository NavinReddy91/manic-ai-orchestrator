import asyncio
import json
import logging
import shutil
import tempfile
from celery import Celery
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import AgentRun, Task
from .org_chart import ORG_CHART
from .llm import delegate, review, run_worker
from .git_ops import (
    clone_repo,
    create_branch,
    write_files,
    commit_and_push,
    open_pull_request,
)
from .github_oauth import get_github_token

logger = logging.getLogger(__name__)

celery_app = Celery(
    "nexus_orchestrator", broker=settings.redis_url, backend=settings.redis_url
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
)

MAX_REVISIONS_PER_AGENT = 2


def _children(db: Session, parent_id: str) -> list[AgentRun]:
    return (
        db.query(AgentRun)
        .filter_by(parent_id=parent_id)
        .order_by(AgentRun.order_index)
        .all()
    )


def _compile_context(children: list[AgentRun]) -> str:
    parts = []
    for c in children:
        label = ORG_CHART[c.agent_key]["label"]
        parts.append(f"[{label} — {c.status}]\n{c.result or '(no result)'}")
    return "\n\n".join(parts)


def _try_acquire_review(db: Session, parent_id: str) -> bool:
    """
    Atomic guard: attempt to transition the parent from 'awaiting_children' to
    'reviewing'. Returns True only if THIS caller won the race. Prevents two
    Celery workers from both triggering the manager's review step when sibling
    tasks finish at nearly the same moment.
    """
    from sqlalchemy import update

    result = db.execute(
        update(AgentRun)
        .where(AgentRun.id == parent_id, AgentRun.status == "awaiting_children")
        .values(status="reviewing")
    )
    db.commit()
    return result.rowcount > 0


async def _run_git_worker(
    db: Session, task: Task, agent_run: AgentRun, node: dict, context: str
) -> str:
    token = get_github_token(db, task.user_id, task.organization_id)
    if not token:
        raise RuntimeError(
            "GitHub isn't connected for this organization yet — connect it first."
        )
    if not task.repo:
        raise RuntimeError("No repo set on this task — coding agents need one.")

    workdir = tempfile.mkdtemp(prefix="nexus_")
    try:
        repo_path, branch_existed = clone_repo(
            task.repo, token, workdir, branch=task.branch
        )
        branch = task.branch or f"nexus/{task.id[:8]}"
        if not branch_existed:
            create_branch(repo_path, branch)
            task.branch = branch
            db.commit()

        raw = await run_worker(
            agent_run.agent_key,
            node["system"],
            agent_run.instructions,
            context,
            node.get("uses_browse", False),
        )
        parsed = json.loads(raw)
        files = parsed.get("files", [])
        summary = parsed.get("summary", "change")

        if files:
            write_files(repo_path, files)
            commit_and_push(
                repo_path, branch, f"{node['label']}: {summary}", token, task.repo
            )

        return json.dumps(
            {"summary": summary, "files_changed": [f["path"] for f in files]}
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


async def _execute_leaf(
    db: Session, task: Task, agent_run: AgentRun, node: dict, context: str
) -> str:
    if node.get("uses_git"):
        return await _run_git_worker(db, task, agent_run, node, context)
    return await run_worker(
        agent_run.agent_key,
        node["system"],
        agent_run.instructions,
        context,
        node.get("uses_browse", False),
    )


@celery_app.task(
    name="run_agent_node",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def run_agent_node(self, agent_run_id: str):
    """
    Runs exactly one node in the org chart. Managers delegate to their direct
    reports and stop (their own completion is driven later, from
    _on_child_finished, once every report is in). Leaf workers do real work —
    git changes, live web research, or a plain LLM call — then immediately
    notify their parent.
    """
    db: Session = SessionLocal()
    try:
        agent_run = db.query(AgentRun).filter_by(id=agent_run_id).first()
        if not agent_run:
            return
        task = db.query(Task).filter_by(id=agent_run.task_id).first()
        node = ORG_CHART[agent_run.agent_key]

        logger.info(
            "Agent node starting",
            extra={"task_id": task.id, "agent_key": agent_run.agent_key},
        )

        agent_run.status = "running"
        db.commit()

        if node["reports"]:
            _dispatch_manager(db, task, agent_run, node)
        else:
            parent_context = ""
            if agent_run.parent_id:
                siblings_done = [
                    c
                    for c in _children(db, agent_run.parent_id)
                    if c.order_index < agent_run.order_index and c.status == "done"
                ]
                parent_context = _compile_context(siblings_done)

            result = asyncio.run(
                _execute_leaf(db, task, agent_run, node, parent_context)
            )
            agent_run.status = "done"
            agent_run.result = result
            db.commit()
            _on_child_finished(db, agent_run)

    except Exception as e:
        db.rollback()
        logger.exception(
            "Agent node failed",
            extra={"agent_key": agent_run.agent_key if "agent_run" in dir() else None},
        )
        agent_run = db.query(AgentRun).filter_by(id=agent_run_id).first()
        if agent_run:
            agent_run.status = "failed"
            agent_run.result = str(e)
            db.commit()
            _on_child_finished(db, agent_run)
    finally:
        db.close()


def _dispatch_manager(db: Session, task: Task, agent_run: AgentRun, node: dict):
    existing_children = _children(db, agent_run.id)
    if not existing_children:
        planned = asyncio.run(delegate(node["system"], agent_run.instructions))
        if not planned:
            planned = [
                {
                    "agent_key": node["reports"][0],
                    "instructions": agent_run.instructions,
                }
            ]
        for i, item in enumerate(planned):
            db.add(
                AgentRun(
                    task_id=task.id,
                    parent_id=agent_run.id,
                    agent_key=item["agent_key"],
                    instructions=item["instructions"],
                    order_index=i,
                    status="pending",
                )
            )
        agent_run.status = "awaiting_children"
        db.commit()
        existing_children = _children(db, agent_run.id)

    if node.get("sequential"):
        first = existing_children[0]
        run_agent_node.delay(first.id)
    else:
        for c in existing_children:
            run_agent_node.delay(c.id)


def _on_child_finished(db: Session, child: AgentRun):
    if not child.parent_id:
        return  # CEO itself finished — handled by _finalize_task from its own review step

    parent = db.query(AgentRun).filter_by(id=child.parent_id).first()
    parent_node = ORG_CHART[parent.agent_key]
    siblings = _children(db, parent.id)

    if parent_node.get("sequential"):
        next_sibling = next(
            (s for s in siblings if s.order_index == child.order_index + 1), None
        )
        if next_sibling and next_sibling.status == "pending":
            run_agent_node.delay(next_sibling.id)
            return
        if any(
            s.status == "running"
            or (s.status == "pending" and s.order_index < child.order_index)
            for s in siblings
        ):
            return  # earlier step still catching up
    else:
        if any(s.status in ("pending", "running") for s in siblings):
            return  # still waiting on other parallel siblings

    # --- Atomic guard: only ONE worker proceeds to review ---
    if not _try_acquire_review(db, parent.id):
        logger.info(
            "Review already claimed by another worker",
            extra={"agent_key": parent.agent_key},
        )
        return

    if any(s.status == "failed" for s in siblings):
        parent.status = "failed"
        parent.result = "One or more team members failed: " + _compile_context(
            [s for s in siblings if s.status == "failed"]
        )
        db.commit()
        _propagate(db, parent)
        return

    decision = asyncio.run(
        review(parent_node["review_system"], _compile_context(siblings))
    )

    if decision.get("decision") == "revise" and decision.get("revisions"):
        applied_any = False
        for rev in decision["revisions"]:
            target = next(
                (s for s in siblings if s.agent_key == rev["agent_key"]), None
            )
            if not target or target.revision_count >= MAX_REVISIONS_PER_AGENT:
                continue
            applied_any = True
            target.instructions = rev["instructions"]
            target.status = "pending"
            target.revision_count += 1
            if parent_node.get("sequential"):
                for later in siblings:
                    if later.order_index > target.order_index:
                        later.status = "pending"
        db.commit()

        if applied_any:
            if parent_node.get("sequential"):
                restart_point = min(
                    (s for s in siblings if s.status == "pending"),
                    key=lambda s: s.order_index,
                )
                run_agent_node.delay(restart_point.id)
            else:
                for s in siblings:
                    if s.status == "pending":
                        run_agent_node.delay(s.id)
            return
        # every requested revision had already hit its cap — fall through to approve

    parent.status = "done"
    parent.result = json.dumps(
        {"summary": decision.get("summary", "Team completed its work.")}
    )

    if parent.agent_key == "coding_head" and task.repo and task.branch:
        try:
            token = get_github_token(db, task.user_id, task.organization_id)
            pr_url = asyncio.run(
                open_pull_request(
                    task.repo,
                    token,
                    task.branch,
                    base="main",
                    title=f"Nexus: {task.prompt[:100]}",
                    body=decision.get(
                        "summary", "Automated change from the Nexus coding team."
                    ),
                )
            )
            parent.result = json.dumps(
                {
                    "summary": decision.get("summary", "Team completed its work."),
                    "pr_url": pr_url,
                }
            )
        except Exception as e:
            parent.result = json.dumps(
                {
                    "summary": decision.get("summary", "Team completed its work."),
                    "pr_error": str(e),
                }
            )

    db.commit()
    _propagate(db, parent)


def _propagate(db: Session, finished_manager: AgentRun):
    if finished_manager.parent_id:
        _on_child_finished(db, finished_manager)
        return

    # This manager had no parent — it was the CEO. Finalize the whole task.
    task = db.query(Task).filter_by(id=finished_manager.task_id).first()
    try:
        result = json.loads(finished_manager.result) if finished_manager.result else {}
    except json.JSONDecodeError:
        result = {}
    task.final_report = result.get("summary", finished_manager.result)
    task.status = (
        "failed"
        if finished_manager.status == "failed"
        else ("review" if task.branch else "done")
    )
    db.commit()

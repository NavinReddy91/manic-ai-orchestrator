"""
Manic AI — In-Process Background Worker
Replaces Celery for simpler deployment (Render free tier, etc.)
Uses asyncio to run agent tasks in the background.
"""

import asyncio
import json
import logging
import shutil
import tempfile
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import AgentRun, Task, OrgAgentOverride
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
from .webhook import send_webhook

logger = logging.getLogger(__name__)

MAX_REVISIONS_PER_AGENT = 2

# Track running tasks to prevent duplicates
_running_tasks = set()


async def execute_agent_node(agent_run_id: str):
    """
    Runs exactly one node in the org chart. Managers delegate to their direct
    reports and stop. Leaf workers do real work.
    """
    db: Session = SessionLocal()
    try:
        agent_run = db.query(AgentRun).filter_by(id=agent_run_id).first()
        if not agent_run:
            return

        task = db.query(Task).filter_by(id=agent_run.task_id).first()
        if not task:
            return

        # Check if task was cancelled
        if task.status == "cancelled":
            agent_run.status = "cancelled"
            agent_run.completed_at = datetime.utcnow()
            db.commit()
            return

        node = ORG_CHART[agent_run.agent_key]

        logger.info(
            f"Agent node starting: {agent_run.agent_key}",
            extra={"task_id": task.id, "agent_key": agent_run.agent_key},
        )

        # Mark as running and set started_at
        agent_run.status = "running"
        agent_run.started_at = datetime.utcnow()

        # Set task started_at if this is the CEO (root agent)
        if not agent_run.parent_id and not task.started_at:
            task.started_at = datetime.utcnow()

        db.commit()

        if node["reports"]:
            await _dispatch_manager(db, task, agent_run, node)
        else:
            parent_context = ""
            if agent_run.parent_id:
                siblings_done = [
                    c
                    for c in _children(db, agent_run.parent_id)
                    if c.order_index < agent_run.order_index and c.status == "done"
                ]
                parent_context = _compile_context(siblings_done)

            result = await _execute_leaf(db, task, agent_run, node, parent_context)
            agent_run.status = "done"
            agent_run.result = result
            agent_run.completed_at = datetime.utcnow()
            db.commit()
            await _on_child_finished(db, agent_run)

    except Exception as e:
        db.rollback()
        logger.exception(
            f"Agent node failed: {agent_run.agent_key if 'agent_run' in locals() else 'unknown'}"
        )
        agent_run = db.query(AgentRun).filter_by(id=agent_run_id).first()
        if agent_run:
            agent_run.status = "failed"
            agent_run.result = str(e)
            agent_run.completed_at = datetime.utcnow()
            db.commit()
            await _on_child_finished(db, agent_run)
    finally:
        db.close()


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
    'reviewing'. Returns True only if THIS caller won the race.
    """
    from sqlalchemy import update

    result = db.execute(
        update(AgentRun)
        .where(AgentRun.id == parent_id, AgentRun.status == "awaiting_children")
        .values(status="reviewing")
    )
    db.commit()
    return result.rowcount > 0


def _is_task_cancelled(db: Session, task_id: str) -> bool:
    """Check if the task has been cancelled."""
    task = db.query(Task).filter_by(id=task_id).first()
    return task and task.status == "cancelled"


def _get_agent_system_prompt(db: Session, agent_key: str, organization_id: str) -> str:
    """
    Get the system prompt for an agent, checking for org-specific overrides first.
    """
    override = (
        db.query(OrgAgentOverride)
        .filter_by(agent_key=agent_key, organization_id=organization_id)
        .first()
    )
    if override:
        return override.system_prompt_override
    return ORG_CHART[agent_key]["system"]


def _generate_unique_branch_name(task_id: str, existing_branches: list[str]) -> str:
    """
    Generate a unique branch name to avoid conflicts with concurrent tasks.
    """
    base = f"manic/{task_id[:8]}"
    if base not in existing_branches:
        return base

    # Add a suffix to make it unique
    counter = 1
    while f"{base}-{counter}" in existing_branches:
        counter += 1
    return f"{base}-{counter}"


def _validate_file_sizes(files: list[dict]) -> None:
    """
    Validate that files don't exceed size limits.
    """
    if len(files) > settings.max_files_per_commit:
        raise ValueError(
            f"Too many files: {len(files)} > {settings.max_files_per_commit}"
        )

    for f in files:
        content_size = len(f.get("content", "").encode("utf-8"))
        if content_size > settings.max_file_size_bytes:
            raise ValueError(
                f"File {f.get('path', 'unknown')} too large: {content_size} bytes > {settings.max_file_size_bytes}"
            )


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

    workdir = tempfile.mkdtemp(prefix="manic_")
    try:
        repo_path, branch_existed = clone_repo(
            task.repo, token, workdir, branch=task.branch
        )

        # Generate unique branch name if needed
        if not task.branch:
            task.branch = _generate_unique_branch_name(task.id, [])
            db.commit()

        branch = task.branch
        if not branch_existed:
            create_branch(repo_path, branch)
            db.commit()

        # Check for cancellation before expensive LLM call
        if _is_task_cancelled(db, task.id):
            return json.dumps({"summary": "Task was cancelled", "files_changed": []})

        # Get org-specific system prompt if available
        system_prompt = _get_agent_system_prompt(
            db, agent_run.agent_key, task.organization_id
        )

        raw = await run_worker(
            agent_run.agent_key,
            system_prompt,
            agent_run.instructions,
            context,
            node.get("uses_browse", False),
        )

        # Check for cancellation after LLM call
        if _is_task_cancelled(db, task.id):
            return json.dumps({"summary": "Task was cancelled", "files_changed": []})

        parsed = json.loads(raw)
        files = parsed.get("files", [])
        summary = parsed.get("summary", "change")

        # Validate file sizes
        _validate_file_sizes(files)

        if files:
            write_files(repo_path, files)
            commit_and_push(
                repo_path, branch, f"{node['label']}: {summary}", token, task.repo
            )

        # Track LLM call and estimate tokens
        task.llm_call_count += 1
        task.estimated_tokens += len(raw) // 4  # rough estimate

        return json.dumps(
            {"summary": summary, "files_changed": [f["path"] for f in files]}
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


async def _execute_leaf(
    db: Session, task: Task, agent_run: AgentRun, node: dict, context: str
) -> str:
    # Check for cancellation
    if _is_task_cancelled(db, task.id):
        return json.dumps({"summary": "Task was cancelled"})

    # Get org-specific system prompt if available
    system_prompt = _get_agent_system_prompt(
        db, agent_run.agent_key, task.organization_id
    )

    if node.get("uses_git"):
        return await _run_git_worker(db, task, agent_run, node, context)

    result = await run_worker(
        agent_run.agent_key,
        system_prompt,
        agent_run.instructions,
        context,
        node.get("uses_browse", False),
    )

    # Track LLM call and estimate tokens
    task.llm_call_count += 1
    task.estimated_tokens += len(result) // 4  # rough estimate

    return result


async def _dispatch_manager(db: Session, task: Task, agent_run: AgentRun, node: dict):
    # Check for cancellation
    if _is_task_cancelled(db, task.id):
        agent_run.status = "cancelled"
        agent_run.completed_at = datetime.utcnow()
        db.commit()
        return

    existing_children = _children(db, agent_run.id)
    if not existing_children:
        # Get org-specific system prompt if available
        system_prompt = _get_agent_system_prompt(
            db, agent_run.agent_key, task.organization_id
        )

        planned = await delegate(system_prompt, agent_run.instructions)
        if not planned:
            planned = [
                {
                    "agent_key": node["reports"][0],
                    "instructions": agent_run.instructions,
                }
            ]

        # Track LLM call
        task.llm_call_count += 1

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
        # Sequential execution: run children one after another
        for c in existing_children:
            await execute_agent_node(c.id)
    else:
        # Parallel execution: run all children concurrently
        await asyncio.gather(*[execute_agent_node(c.id) for c in existing_children])


async def _on_child_finished(db: Session, child: AgentRun):
    if not child.parent_id:
        # CEO finished — finalize the task
        await _finalize_task(db, child)
        return

    # Check for cancellation
    task = db.query(Task).filter_by(id=child.task_id).first()
    if task and task.status == "cancelled":
        return

    parent = db.query(AgentRun).filter_by(id=child.parent_id).first()
    parent_node = ORG_CHART[parent.agent_key]
    siblings = _children(db, parent.id)

    # Check if all siblings are done
    if any(s.status in ("pending", "running") for s in siblings):
        return

    # Atomic guard: only ONE worker proceeds to review
    if not _try_acquire_review(db, parent.id):
        logger.info(
            f"Review already claimed for {parent.agent_key}",
            extra={"agent_key": parent.agent_key},
        )
        return

    if any(s.status == "failed" for s in siblings):
        parent.status = "failed"
        parent.result = "One or more team members failed: " + _compile_context(
            [s for s in siblings if s.status == "failed"]
        )
        parent.completed_at = datetime.utcnow()
        db.commit()
        await _propagate(db, parent)
        return

    # Check for cancellation before review
    if _is_task_cancelled(db, child.task_id):
        parent.status = "cancelled"
        parent.completed_at = datetime.utcnow()
        db.commit()
        await _propagate(db, parent)
        return

    # Get org-specific review prompt if available
    review_prompt = _get_agent_system_prompt(
        db, parent.agent_key + "_review", task.organization_id
    )
    if review_prompt == ORG_CHART[parent.agent_key]["system"]:
        # No override, use default review_system
        review_prompt = parent_node["review_system"]

    decision = await review(review_prompt, _compile_context(siblings))

    # Track LLM call
    task.llm_call_count += 1

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
        db.commit()

        if applied_any:
            # Re-run pending siblings
            pending_siblings = [s for s in siblings if s.status == "pending"]
            if parent_node.get("sequential"):
                for s in pending_siblings:
                    await execute_agent_node(s.id)
            else:
                await asyncio.gather(
                    *[execute_agent_node(s.id) for s in pending_siblings]
                )
            return

    parent.status = "done"
    parent.result = json.dumps(
        {"summary": decision.get("summary", "Team completed its work.")}
    )
    parent.completed_at = datetime.utcnow()

    if parent.agent_key == "coding_head" and task.repo and task.branch:
        try:
            token = get_github_token(db, task.user_id, task.organization_id)
            pr_url = await open_pull_request(
                task.repo,
                token,
                task.branch,
                base="main",
                title=f"Manic: {task.prompt[:100]}",
                body=decision.get(
                    "summary", "Automated change from the Manic coding team."
                ),
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
    await _propagate(db, parent)


async def _propagate(db: Session, finished_manager: AgentRun):
    if finished_manager.parent_id:
        await _on_child_finished(db, finished_manager)
        return

    # This manager had no parent — it was the CEO. Finalize the whole task.
    await _finalize_task(db, finished_manager)


async def _finalize_task(db: Session, ceo_run: AgentRun):
    """Finalize the task when the CEO completes."""
    task = db.query(Task).filter_by(id=ceo_run.task_id).first()
    if not task:
        return

    try:
        result = json.loads(ceo_run.result) if ceo_run.result else {}
    except json.JSONDecodeError:
        result = {}

    task.final_report = result.get("summary", ceo_run.result)
    task.status = (
        "failed"
        if ceo_run.status == "failed"
        else ("review" if task.branch else "done")
    )
    task.completed_at = datetime.utcnow()
    db.commit()

    # Send webhook if configured
    if task.callback_url:
        try:
            await send_webhook(task)
        except Exception as e:
            logger.error(f"Failed to send webhook for task {task.id}: {e}")


async def start_task_execution(task_id: str, user_id: str):
    """
    Start executing a task in the background.
    Creates the CEO agent run and begins execution.
    """
    if task_id in _running_tasks:
        logger.warning(f"Task {task_id} is already running")
        return

    _running_tasks.add(task_id)
    try:
        db = SessionLocal()
        try:
            task = db.query(Task).filter_by(id=task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            # Create CEO agent run
            ceo_run = AgentRun(
                task_id=task.id,
                parent_id=None,
                agent_key="ceo",
                instructions=task.prompt,
                order_index=0,
                status="pending",
            )
            db.add(ceo_run)
            task.status = "running"
            db.commit()
            db.refresh(ceo_run)

            # Start execution
            await execute_agent_node(ceo_run.id)
        finally:
            db.close()
    except Exception as e:
        logger.exception(f"Failed to execute task {task_id}")
        # Mark task as failed
        db = SessionLocal()
        try:
            task = db.query(Task).filter_by(id=task_id).first()
            if task:
                task.status = "failed"
                task.final_report = f"Execution failed: {str(e)}"
                task.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
    finally:
        _running_tasks.discard(task_id)

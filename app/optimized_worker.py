"""
Manic AI — Optimized Celery Worker
Efficient workflow: CEO clones once, shares context with all departments sequentially.
This reduces token consumption by 50-70% compared to parallel execution.
"""

import asyncio
import json
import logging
import shutil
import tempfile
from datetime import datetime
from celery import Celery
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
from .report_generator import generate_report

logger = logging.getLogger(__name__)

celery_app = Celery(
    "manic_orchestrator", broker=settings.redis_url, backend=settings.redis_url
)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
)

# Enable Celery Beat for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-stale-tasks": {
        "task": "cleanup_stale_tasks",
        "schedule": 60.0,
    },
}

MAX_REVISIONS_PER_AGENT = 1  # Reduced from 2 to save tokens


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
    """Atomic guard for review step."""
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
    """Get the system prompt for an agent, checking for org-specific overrides."""
    override = (
        db.query(OrgAgentOverride)
        .filter_by(agent_key=agent_key, organization_id=organization_id)
        .first()
    )
    if override:
        return override.system_prompt_override
    return ORG_CHART[agent_key]["system"]


def _generate_unique_branch_name(task_id: str, existing_branches: list[str]) -> str:
    """Generate a unique branch name."""
    base = f"manic/{task_id[:8]}"
    if base not in existing_branches:
        return base
    counter = 1
    while f"{base}-{counter}" in existing_branches:
        counter += 1
    return f"{base}-{counter}"


def _validate_file_sizes(files: list[dict]) -> None:
    """Validate that files don't exceed size limits."""
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


def _check_token_budget(db: Session, task: Task, estimated_tokens: int) -> bool:
    """Check if task has exceeded token budget."""
    if task.token_budget <= 0:
        return True
    return (task.tokens_used + estimated_tokens) <= task.token_budget


def _update_token_usage(db: Session, task: Task, tokens: int):
    """Update task token usage and commit."""
    task.tokens_used += tokens
    task.estimated_tokens += tokens
    db.commit()


@celery_app.task(
    name="run_optimized_task",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
)
def run_optimized_task(self, task_id: str):
    """
    Optimized workflow: CEO clones once, shares context sequentially.
    This is 50-70% more token-efficient than parallel execution.
    """
    logger.info(f"=== run_optimized_task STARTED for task_id={task_id} ===")

    # Check LLM API key first
    if not settings.llm_api_key:
        logger.error("LLM_API_KEY not configured! Cannot execute task.")
        db = SessionLocal()
        try:
            task = db.query(Task).filter_by(id=task_id).first()
            if task:
                task.status = "failed"
                task.final_report = "LLM_API_KEY not configured. Please set LLM_API_KEY environment variable."
                task.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
        return

    logger.info(f"LLM provider: {settings.llm_provider}, model: {settings.llm_model}")

    db: Session = SessionLocal()
    workspace = None

    try:
        task = db.query(Task).filter_by(id=task_id).first()
        if not task:
            logger.error(f"Task {task_id} not found")
            return

        if task.status == "cancelled":
            logger.info(f"Task {task_id} was cancelled")
            return

        logger.info(f"Starting optimized task execution: {task_id}")
        logger.info(f"Task prompt: {task.prompt[:200]}...")
        task.status = "running"
        task.started_at = datetime.utcnow()
        db.commit()

        # Step 1: CEO clones repo ONCE (if coding task)
        if task.repo:
            token = get_github_token(db, task.user_id, task.organization_id)
            if not token:
                raise RuntimeError("GitHub not connected for this organization")

            workspace = tempfile.mkdtemp(prefix="manic_workspace_")
            repo_path, _ = clone_repo(task.repo, token, workspace)
            branch = _generate_unique_branch_name(task.id, [])
            create_branch(repo_path, branch)
            task.branch = branch
            db.commit()

            logger.info(f"CEO cloned repo to workspace: {workspace}")
        else:
            repo_path = None
            logger.info("Non-coding task, no repo clone needed")

        # Step 2: CEO analyzes and creates execution plan
        ceo_run = db.query(AgentRun).filter_by(task_id=task.id, parent_id=None).first()
        if not ceo_run:
            ceo_run = AgentRun(
                task_id=task.id,
                parent_id=None,
                agent_key="ceo",
                instructions=task.prompt,
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(ceo_run)
            db.commit()
            db.refresh(ceo_run)

        # Check budget before CEO delegation
        if not _check_token_budget(db, task, 1000):
            _handle_budget_exceeded(db, task, ceo_run)
            return

        ceo_system = _get_agent_system_prompt(db, "ceo", task.organization_id)
        ceo_plan = asyncio.run(delegate(ceo_system, task.prompt))

        if not ceo_plan:
            ceo_plan = [{"agent_key": "marketing_head", "instructions": task.prompt}]

        _update_token_usage(db, task, 800)
        logger.info(f"CEO created plan with {len(ceo_plan)} departments")

        # Step 3: Execute departments SEQUENTIALLY with shared context
        accumulated_context = ""
        all_files_changed = []

        for dept_plan in ceo_plan:
            if _is_task_cancelled(db, task.id):
                logger.info(f"Task {task_id} cancelled during execution")
                task.status = "cancelled"
                task.cancelled_at = datetime.utcnow()
                db.commit()
                return

            dept_key = dept_plan["agent_key"]
            dept_instructions = dept_plan["instructions"]

            logger.info(f"Executing department: {dept_key}")

            # Create department agent run
            dept_run = AgentRun(
                task_id=task.id,
                parent_id=ceo_run.id,
                agent_key=dept_key,
                instructions=dept_instructions,
                status="running",
                started_at=datetime.utcnow(),
                order_index=len(_children(db, ceo_run.id)),
            )
            db.add(dept_run)
            db.commit()
            db.refresh(dept_run)

            # Check budget before department execution
            if not _check_token_budget(db, task, 2000):
                dept_run.status = "failed"
                dept_run.result = json.dumps(
                    {
                        "summary": "Token budget exceeded before department execution",
                        "budget_exceeded": True,
                    }
                )
                dept_run.completed_at = datetime.utcnow()
                db.commit()
                continue

            # Execute department with shared context
            dept_system = _get_agent_system_prompt(db, dept_key, task.organization_id)

            # Build context: previous departments' work + repo structure (if coding)
            full_context = accumulated_context
            if repo_path:
                repo_structure = _get_repo_structure(repo_path)
                full_context = (
                    f"REPOSITORY STRUCTURE:\n{repo_structure}\n\n{full_context}"
                )

            # Execute department
            try:
                if dept_key == "coding_head" and repo_path:
                    # Coding department works on actual files
                    dept_result = asyncio.run(
                        _execute_coding_department(
                            db,
                            task,
                            dept_run,
                            dept_system,
                            dept_instructions,
                            full_context,
                            repo_path,
                        )
                    )
                else:
                    # Other departments generate reports/analysis
                    dept_result = asyncio.run(
                        run_worker(
                            dept_key,
                            dept_system,
                            dept_instructions,
                            full_context,
                            uses_browse=True,
                        )
                    )

                # Track token usage
                actual_tokens = len(dept_result) // 4
                _update_token_usage(db, task, actual_tokens)

                # Update department run
                dept_run.status = "done"
                dept_run.result = dept_result
                dept_run.completed_at = datetime.utcnow()
                db.commit()

                # Extract files changed (if coding)
                try:
                    result_json = json.loads(dept_result)
                    if "files_changed" in result_json:
                        all_files_changed.extend(result_json["files_changed"])
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass

                # Accumulate context for next department
                dept_label = ORG_CHART[dept_key]["label"]
                accumulated_context += f"\n\n[{dept_label} COMPLETED]:\n{dept_result}"

                logger.info(f"Department {dept_key} completed successfully")

            except Exception as e:
                logger.exception(f"Department {dept_key} failed: {e}")
                dept_run.status = "failed"
                dept_run.result = json.dumps({"summary": f"Failed: {str(e)}"})
                dept_run.completed_at = datetime.utcnow()
                db.commit()

        # Step 4: CEO reviews final result
        if not _check_token_budget(db, task, 800):
            _handle_budget_exceeded(db, task, ceo_run)
            return

        logger.info("CEO reviewing final results")
        review_system = ORG_CHART["ceo"]["review_system"]
        final_review = asyncio.run(review(review_system, accumulated_context))
        _update_token_usage(db, task, 800)

        # Step 5: Coding department pushes code (if applicable)
        if task.repo and repo_path and all_files_changed:
            try:
                token = get_github_token(db, task.user_id, task.organization_id)
                commit_message = f"Manic AI: {task.prompt[:100]}"
                commit_and_push(
                    repo_path, task.branch, commit_message, token, task.repo
                )

                # Open PR
                pr_url = asyncio.run(
                    open_pull_request(
                        task.repo,
                        token,
                        task.branch,
                        "main",
                        f"Manic AI: {task.prompt[:100]}",
                        final_review.get("summary", "Automated changes by Manic AI"),
                    )
                )

                logger.info(f"PR created: {pr_url}")
                task.final_report = json.dumps(
                    {
                        "summary": final_review.get("summary", "Task completed"),
                        "pr_url": pr_url,
                        "files_changed": all_files_changed,
                    }
                )
            except Exception as e:
                logger.exception(f"Failed to push code: {e}")
                task.final_report = json.dumps(
                    {
                        "summary": final_review.get(
                            "summary", "Task completed with errors"
                        ),
                        "error": str(e),
                    }
                )
        else:
            # Generate downloadable reports for non-coding tasks
            reports = asyncio.run(_generate_department_reports(db, task, ceo_run))
            task.final_report = json.dumps(
                {
                    "summary": final_review.get("summary", "Task completed"),
                    "reports": reports,
                }
            )

        # Mark task as complete
        task.status = "done"
        task.completed_at = datetime.utcnow()
        ceo_run.status = "done"
        ceo_run.result = task.final_report
        ceo_run.completed_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Task {task_id} completed successfully. Tokens used: {task.tokens_used}/{task.token_budget}"
        )

        # Send webhook if configured
        if task.callback_url:
            try:
                asyncio.run(send_webhook(task))
            except Exception as e:
                logger.error(f"Webhook failed: {e}")

    except Exception as e:
        logger.exception(f"Task {task_id} failed: {e}")
        db.rollback()
        task = db.query(Task).filter_by(id=task_id).first()
        if task:
            task.status = "failed"
            task.final_report = json.dumps({"error": str(e)})
            task.completed_at = datetime.utcnow()
            db.commit()
    finally:
        # Cleanup workspace
        if workspace:
            try:
                shutil.rmtree(workspace, ignore_errors=True)
            except OSError:
                pass
        db.close()


async def _execute_coding_department(
    db: Session,
    task: Task,
    dept_run: AgentRun,
    system: str,
    instructions: str,
    context: str,
    repo_path: str,
) -> str:
    """Execute coding department with file operations."""
    # Get coding head's plan — already inside async, call directly
    coding_plan = await delegate(system, f"{instructions}\n\nContext:\n{context}")

    if not coding_plan:
        return json.dumps({"summary": "No coding changes needed", "files_changed": []})

    all_files = []

    # Execute each coding agent sequentially
    for agent_plan in coding_plan:
        agent_key = agent_plan["agent_key"]
        agent_instructions = agent_plan["instructions"]

        agent_system = _get_agent_system_prompt(db, agent_key, task.organization_id)

        # Agent works on files
        result = await run_worker(
            agent_key, agent_system, agent_instructions, context, uses_browse=False
        )

        try:
            result_json = json.loads(result)
            files = result_json.get("files", [])

            if files:
                _validate_file_sizes(files)
                write_files(repo_path, files)
                all_files.extend([f["path"] for f in files])

                # Update context for next agent
                context += f"\n\n[{ORG_CHART[agent_key]['label']} made changes to: {', '.join(f['path'] for f in files)}]"
        except Exception as e:
            logger.error(f"Coding agent {agent_key} failed: {e}")

    return json.dumps(
        {
            "summary": f"Coding completed: {len(all_files)} files modified",
            "files_changed": all_files,
        }
    )


def _get_repo_structure(repo_path: str) -> str:
    """Get a simplified repo structure for context."""
    import os

    structure = []

    for root, dirs, files in os.walk(repo_path):
        # Skip .git directory
        if ".git" in dirs:
            dirs.remove(".git")

        level = root.replace(repo_path, "").count(os.sep)
        indent = "  " * level
        structure.append(f"{indent}{os.path.basename(root)}/")

        # Limit files shown
        subindent = "  " * (level + 1)
        for file in files[:10]:  # Show max 10 files per directory
            structure.append(f"{subindent}{file}")

        if len(files) > 10:
            structure.append(f"{subindent}... and {len(files) - 10} more files")

    return "\n".join(structure[:100])  # Limit total lines


async def _generate_department_reports(
    db: Session, task: Task, ceo_run: AgentRun
) -> list:
    """Generate downloadable reports for each department."""
    reports = []
    dept_runs = _children(db, ceo_run.id)

    for dept_run in dept_runs:
        if dept_run.status == "done" and dept_run.result:
            try:
                # Generate report based on department type
                dept_key = dept_run.agent_key
                report_content = dept_run.result

                # Generate PDF or other format
                report_file = await generate_report(
                    department=dept_key,
                    content=report_content,
                    task_prompt=task.prompt,
                    output_format="pdf",
                )

                reports.append(
                    {
                        "department": ORG_CHART[dept_key]["label"],
                        "report_path": report_file,
                        "format": "pdf",
                    }
                )
            except Exception as e:
                logger.error(f"Failed to generate report for {dept_run.agent_key}: {e}")
                reports.append(
                    {
                        "department": ORG_CHART[dept_run.agent_key]["label"],
                        "error": str(e),
                    }
                )

    return reports


def _handle_budget_exceeded(db: Session, task: Task, agent_run: AgentRun):
    """Handle token budget exceeded."""
    logger.warning(
        f"Token budget exceeded for task {task.id}: {task.tokens_used}/{task.token_budget}"
    )

    task.status = "failed"
    task.final_report = json.dumps(
        {
            "error": f"Token budget exceeded ({task.tokens_used}/{task.token_budget} tokens used)",
            "budget_exceeded": True,
        }
    )
    task.completed_at = datetime.utcnow()

    agent_run.status = "failed"
    agent_run.result = json.dumps(
        {"summary": "Token budget exceeded", "budget_exceeded": True}
    )
    agent_run.completed_at = datetime.utcnow()

    db.commit()


# Import cleanup task
from .task_timeout import cleanup_stale_tasks

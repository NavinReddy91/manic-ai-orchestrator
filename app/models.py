import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer,
    Boolean,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _uuid():
    return str(uuid.uuid4())


class Organization(Base):
    """
    A real business boundary. Every Task and every ConnectedAccount belongs to
    exactly one Organization. Agents never see across this line — a task
    running under "LFS Loans" has no path to a GitHub token or task history
    connected under "DigiMarkIn", even for the same user.
    """

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)  # owner — DigiMarkIn JWT `sub`
    name = Column(String, nullable=False)  # "DigiMarkIn", "LFS Loans", etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tasks = relationship(
        "Task", back_populates="organization", cascade="all, delete-orphan"
    )
    agent_overrides = relationship(
        "OrgAgentOverride", back_populates="organization", cascade="all, delete-orphan"
    )


class ConnectedAccount(Base):
    """One row per (user, organization, provider). Scoped to an org, not just a user."""

    __tablename__ = "connected_accounts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    organization_id = Column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True
    )
    provider = Column(String, nullable=False)  # "github"
    provider_account_login = Column(String, nullable=True)
    encrypted_token = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    """A single top-level user request that goes to the Manic Chief Agent, for ONE organization."""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    organization_id = Column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True
    )
    prompt = Column(Text, nullable=False)
    repo = Column(
        String, nullable=True
    )  # "owner/repo" — only used if the coding team is involved
    branch = Column(String, nullable=True)  # set once the coding team pushes a branch
    status = Column(
        String, default="planning"
    )  # planning | running | review | done | failed | cancelled
    final_report = Column(
        Text, nullable=True
    )  # Chief Agent's compiled summary at the end
    llm_call_count = Column(Integer, default=0)  # tracks LLM API calls for cost control
    estimated_tokens = Column(
        Integer, default=0
    )  # estimated token usage for cost tracking
    priority = Column(Integer, default=0)  # 0=normal, 1=high, 2=urgent
    callback_url = Column(
        String, nullable=True
    )  # webhook URL to POST when task completes
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(
        DateTime, nullable=True
    )  # when the task actually started running
    completed_at = Column(
        DateTime, nullable=True
    )  # when the task finished (any status)
    cancelled_at = Column(DateTime, nullable=True)  # when the task was cancelled

    # Relationships
    organization = relationship("Organization", back_populates="tasks")
    agent_runs = relationship(
        "AgentRun", back_populates="task", cascade="all, delete-orphan"
    )


class AgentRun(Base):
    """
    One node in the org chart's execution tree for this task. The root row is
    the CEO (parent_id is null). Each manager's children are its direct
    reports. `revision_count` tracks how many times a manager has sent this
    node back for a fix.
    """

    __tablename__ = "agent_runs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    task_id = Column(UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=False)
    parent_id = Column(UUID(as_uuid=False), ForeignKey("agent_runs.id"), nullable=True)

    agent_key = Column(String, nullable=False)  # matches a key in org_chart.ORG_CHART
    instructions = Column(Text, nullable=False)
    status = Column(
        String, default="pending"
    )  # pending | running | awaiting_children | reviewing | done | failed | cancelled
    result = Column(Text, nullable=True)
    revision_count = Column(Integer, default=0)
    order_index = Column(
        Integer, default=0
    )  # execution order among siblings, for sequential teams
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="agent_runs")
    children = relationship("AgentRun", backref="parent", remote_side=[id])


class TaskTemplate(Base):
    """Saved task templates for reuse."""

    __tablename__ = "task_templates"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    organization_id = Column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=True, index=True
    )
    name = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OrgAgentOverride(Base):
    """Per-organization overrides for agent system prompts."""

    __tablename__ = "org_agent_overrides"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    organization_id = Column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False, index=True
    )
    agent_key = Column(String, nullable=False)  # matches a key in org_chart.ORG_CHART
    system_prompt_override = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="agent_overrides")


class AuditLog(Base):
    """Audit trail for important actions."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    organization_id = Column(
        UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=True, index=True
    )
    task_id = Column(
        UUID(as_uuid=False), ForeignKey("tasks.id"), nullable=True, index=True
    )
    action = Column(
        String, nullable=False
    )  # task_created, task_cancelled, org_created, etc.
    details = Column(Text, nullable=True)  # JSON with additional context
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

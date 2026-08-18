"""
Manic AI — Database Models
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _uuid():
    return str(uuid.uuid4())


class Organization(Base):
    """
    A business boundary. Every Task and ConnectedAccount belongs to exactly
    one Organization. Agents never see across this boundary.
    """

    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship(
        "Task", back_populates="organization", cascade="all, delete-orphan"
    )
    agent_overrides = relationship(
        "OrgAgentOverride", back_populates="organization", cascade="all, delete-orphan"
    )


class ConnectedAccount(Base):
    """OAuth tokens scoped to (user, organization, provider)."""

    __tablename__ = "connected_accounts"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    organization_id = Column(
        String, ForeignKey("organizations.id"), nullable=False, index=True
    )
    provider = Column(String, nullable=False)  # "github"
    provider_account_login = Column(String, nullable=True)
    encrypted_token = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    """A user request processed by the Manic AI agent hierarchy."""

    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    organization_id = Column(
        String, ForeignKey("organizations.id"), nullable=False, index=True
    )
    prompt = Column(Text, nullable=False)
    repo = Column(String, nullable=True)  # "owner/repo" for coding tasks
    branch = Column(String, nullable=True)
    status = Column(
        String, default="planning"
    )  # planning | running | review | done | failed | cancelled
    final_report = Column(Text, nullable=True)
    llm_call_count = Column(Integer, default=0)
    estimated_tokens = Column(Integer, default=0)
    token_budget = Column(Integer, default=15000)  # Max tokens allowed for this task
    tokens_used = Column(Integer, default=0)  # Actual tokens consumed
    priority = Column(Integer, default=0)  # 0=normal, 1=high, 2=urgent
    callback_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="tasks")
    agent_runs = relationship(
        "AgentRun", back_populates="task", cascade="all, delete-orphan"
    )


class AgentRun(Base):
    """One node in the agent execution tree."""

    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=_uuid)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    parent_id = Column(String, ForeignKey("agent_runs.id"), nullable=True)

    agent_key = Column(String, nullable=False)
    instructions = Column(Text, nullable=False)
    status = Column(
        String, default="pending"
    )  # pending | running | awaiting_children | reviewing | done | failed | cancelled
    result = Column(Text, nullable=True)
    revision_count = Column(Integer, default=0)
    order_index = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="agent_runs")
    children = relationship("AgentRun", backref="parent", remote_side=[id])


class TaskTemplate(Base):
    """Saved task templates for reuse."""

    __tablename__ = "task_templates"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    organization_id = Column(
        String, ForeignKey("organizations.id"), nullable=True, index=True
    )
    name = Column(String, nullable=False)
    prompt = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OrgAgentOverride(Base):
    """Per-organization overrides for agent system prompts."""

    __tablename__ = "org_agent_overrides"

    id = Column(String, primary_key=True, default=_uuid)
    organization_id = Column(
        String, ForeignKey("organizations.id"), nullable=False, index=True
    )
    agent_key = Column(String, nullable=False)
    system_prompt_override = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="agent_overrides")


class AuditLog(Base):
    """Audit trail for important actions."""

    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True)
    organization_id = Column(
        String, ForeignKey("organizations.id"), nullable=True, index=True
    )
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True, index=True)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

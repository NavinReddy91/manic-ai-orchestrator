"""Initial schema with all features

Revision ID: 001_initial
Revises: None
Create Date: 2024-01-01 00:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # Connected accounts table
    op.create_table(
        "connected_accounts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_account_login", sa.String(), nullable=True),
        sa.Column("encrypted_token", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # Tasks table with all new fields
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("repo", sa.String(), nullable=True),
        sa.Column("branch", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("final_report", sa.Text(), nullable=True),
        sa.Column("llm_call_count", sa.Integer(), nullable=True, default=0),
        sa.Column("estimated_tokens", sa.Integer(), nullable=True, default=0),
        sa.Column("priority", sa.Integer(), nullable=True, default=0),
        sa.Column("callback_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
    )

    # Agent runs table with new fields
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("task_id", sa.String(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column(
            "parent_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=True
        ),
        sa.Column("agent_key", sa.String(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("revision_count", sa.Integer(), nullable=True, default=0),
        sa.Column("order_index", sa.Integer(), nullable=True, default=0),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # Task templates table
    op.create_table(
        "task_templates",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # Organization agent overrides table
    op.create_table(
        "org_agent_overrides",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("agent_key", sa.String(), nullable=False),
        sa.Column("system_prompt_override", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )

    # Audit logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column(
            "organization_id",
            sa.String(),
            sa.ForeignKey("organizations.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "task_id", sa.String(), sa.ForeignKey("tasks.id"), nullable=True, index=True
        ),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("org_agent_overrides")
    op.drop_table("task_templates")
    op.drop_table("agent_runs")
    op.drop_table("tasks")
    op.drop_table("connected_accounts")
    op.drop_table("organizations")

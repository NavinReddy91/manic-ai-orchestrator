"""Initial schema

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
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
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
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
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
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("tasks")
    op.drop_table("connected_accounts")
    op.drop_table("organizations")

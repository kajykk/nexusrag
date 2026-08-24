"""baseline: create all tables

Revision ID: 0001
Revises:
Create Date: 2026-07-21 00:00:00

初始迁移：创建 users / datasets / analyses / reports 四张表。
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # datasets
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("table_name", sa.String(length=128), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("column_count", sa.Integer(), nullable=True),
        sa.Column("columns_schema", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("table_name"),
    )

    # analyses
    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=True, server_default="pending"),
        sa.Column("code_type", sa.String(length=16), nullable=True, server_default="python"),
        sa.Column("generated_code", sa.Text(), nullable=True, server_default=""),
        sa.Column("result_data", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("chart_config", sa.Text(), nullable=True, server_default="{}"),
        sa.Column("chart_image", sa.String(length=255), nullable=True, server_default=""),
        sa.Column("error_message", sa.Text(), nullable=True, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # reports
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("analysis_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True, server_default="数据分析报告"),
        sa.Column("content_md", sa.Text(), nullable=True, server_default=""),
        sa.Column("pdf_path", sa.String(length=255), nullable=True, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("analyses")
    op.drop_table("datasets")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

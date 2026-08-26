"""add FK indexes on analyses.dataset_id and reports.analysis_id

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-26 00:00:00

为高频查询路径补建外键索引（此前缺失导致按数据集查分析、
按分析查报告走全表扫描）：
- analyses.dataset_id -> datasets.id
- reports.analysis_id -> analyses.id

使用 batch_alter_table，兼容 SQLite 与 PostgreSQL。
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("analyses") as batch:
        batch.create_index("ix_analyses_dataset_id", ["dataset_id"])
    with op.batch_alter_table("reports") as batch:
        batch.create_index("ix_reports_analysis_id", ["analysis_id"])


def downgrade() -> None:
    with op.batch_alter_table("reports") as batch:
        batch.drop_index("ix_reports_analysis_id")
    with op.batch_alter_table("analyses") as batch:
        batch.drop_index("ix_analyses_dataset_id")

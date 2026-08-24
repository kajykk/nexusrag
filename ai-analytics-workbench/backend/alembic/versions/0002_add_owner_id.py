"""add owner_id to datasets/analyses/reports and backfill

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-24 00:00:00

为三张业务表补充 owner_id 外键（users.id），并回填既有行：
- datasets.owner_id <- 最早注册用户（单用户个人应用的历史数据归属）
- analyses.owner_id <- 其 dataset 的 owner（缺失时回退最早注册用户）
- reports.owner_id  <- 其 analysis 的 owner（缺失时回退最早注册用户）

使用 batch_alter_table，兼容 SQLite（不支持 ALTER ADD CONSTRAINT）与 PostgreSQL。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_owner(table: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))


def _constrain_owner(table: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.create_foreign_key(
            f"fk_{table}_owner_users", "users", ["owner_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_index(f"ix_{table}_owner_id", ["owner_id"])


def _drop_owner(table: str) -> None:
    with op.batch_alter_table(table) as batch:
        batch.drop_index(f"ix_{table}_owner_id")
        batch.drop_constraint(f"fk_{table}_owner_users", type_="foreignkey")
        batch.drop_column("owner_id")


def upgrade() -> None:
    _add_owner("datasets")
    _add_owner("analyses")
    _add_owner("reports")

    # 回填既有行：datasets -> analyses -> reports 按归属链传递
    first_user = "(SELECT id FROM users ORDER BY id LIMIT 1)"
    op.execute(f"UPDATE datasets SET owner_id = {first_user}")
    op.execute(
        "UPDATE analyses SET owner_id = "
        "COALESCE((SELECT d.owner_id FROM datasets d WHERE d.id = analyses.dataset_id), "
        f"{first_user})"
    )
    op.execute(
        "UPDATE reports SET owner_id = "
        "COALESCE((SELECT a.owner_id FROM analyses a WHERE a.id = reports.analysis_id), "
        f"{first_user})"
    )

    _constrain_owner("datasets")
    _constrain_owner("analyses")
    _constrain_owner("reports")


def downgrade() -> None:
    _drop_owner("reports")
    _drop_owner("analyses")
    _drop_owner("datasets")

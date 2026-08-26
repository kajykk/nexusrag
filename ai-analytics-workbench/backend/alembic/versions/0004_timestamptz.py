"""unify timestamps to timestamptz (UTC)

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-26 00:00:00

将四张业务表的时间列统一为 ``timestamptz``：

- users.created_at
- datasets.created_at
- analyses.created_at / analyses.completed_at
- reports.created_at

既有数据为 naive UTC（旧 datetime.utcnow() 写入），使用
``AT TIME ZONE 'UTC'`` 显式声明其 UTC 语义后转为 aware，
避免按数据库会话时区误判。模型默认值同步改为 aware utcnow。

注意：本迁移面向 PostgreSQL；SQLite 开发库为一次性内存/临时库，
无需执行（SQLAlchemy 对 SQLite 忽略 timezone 标志）。
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TARGETS: list[tuple[str, str]] = [
    ("users", "created_at"),
    ("datasets", "created_at"),
    ("analyses", "created_at"),
    ("analyses", "completed_at"),
    ("reports", "created_at"),
]

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    for table, col in _TARGETS:
        op.alter_column(
            table,
            col,
            type_=_TZ,
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for table, col in reversed(_TARGETS):
        # 回退时以 UTC 语义剥离时区，保持 naive UTC 存量格式
        op.alter_column(
            table,
            col,
            type_=sa.DateTime(),
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )

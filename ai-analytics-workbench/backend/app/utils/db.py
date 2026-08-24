"""DataFrame 与 PostgreSQL 之间的 I/O 工具。

安全说明：表名为动态标识符（无法用 bind param 参数化），统一通过
``_validate_table_name`` 严格校验为合法 PostgreSQL 标识符后再插值，
杜绝 SQL 注入。
"""

import re

import pandas as pd
from sqlalchemy import text

from app.db.session import engine

# PostgreSQL 标识符规范：字母/下划线开头，后接字母/数字/下划线，最长 63 字节
# 参考：https://www.postgresql.org/docs/current/sql-syntax-lexical.html#SQL-SYNTAX-IDENTIFIERS
_TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def _validate_table_name(table_name: str) -> None:
    """校验表名是合法的 PostgreSQL 标识符，否则抛出 ValueError。

    用于在 f-string 插值到 SQL 前进行严格校验，避免 SQL 注入。
    """
    if not isinstance(table_name, str) or not _TABLE_NAME_RE.match(table_name):
        raise ValueError(f"非法表名: {table_name!r}")


def dataframe_to_pg(df: pd.DataFrame, table_name: str) -> None:
    """将 DataFrame 写入 PostgreSQL 指定表（覆盖）。"""
    _validate_table_name(table_name)
    df.to_sql(table_name, engine, if_exists="replace", index=False, method="multi")


def load_table_to_dataframe(table_name: str) -> pd.DataFrame:
    """从 PostgreSQL 读取整张表为 DataFrame。"""
    _validate_table_name(table_name)
    with engine.connect() as conn:
        return pd.read_sql(text(f'SELECT * FROM "{table_name}"'), conn)


def get_table_preview(table_name: str, limit: int = 5) -> list[dict]:
    """获取表前 N 行预览。

    表名通过 ``_validate_table_name`` 校验后插值；``limit`` 用 bind param 参数化。
    """
    _validate_table_name(table_name)
    if not isinstance(limit, int) or limit < 0 or limit > 10000:
        raise ValueError(f"非法 limit 值: {limit!r}（应为 0..10000 的整数）")
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(f'SELECT * FROM "{table_name}" LIMIT :limit'),
                {"limit": limit},
            )
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]


def drop_table_if_exists(table_name: str) -> None:
    """安全删除物理表（带表名校验）。

    供 dataset_service.delete_dataset 调用，替代原先的 f-string 拼接。
    """
    _validate_table_name(table_name)
    with engine.connect() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        conn.commit()

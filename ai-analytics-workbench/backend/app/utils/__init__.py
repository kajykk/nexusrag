"""数据集工具：类型推断、schema 提取、安全代码执行。

P1-3 拆分：将原 ``__init__.py`` 中的代码按职责拆分为：
- ``schema.py``  — DataFrame schema 推断与 JSON 序列化
- ``db.py``      — DataFrame <-> PostgreSQL I/O（含表名严格校验）
- ``sandbox.py`` — 受限沙箱执行 Pandas 代码

本 ``__init__.py`` 仅做 re-export，保持向后兼容（已有 services/tests 无需改动）。
"""

from app.utils.db import (
    _validate_table_name,
    dataframe_to_pg,
    drop_table_if_exists,
    get_table_preview,
    load_table_to_dataframe,
)
from app.utils.sandbox import (
    ERROR_EXECUTION,
    ERROR_OK,
    ERROR_TIMEOUT,
    SandboxTimeoutError,
    _validate_sandbox_code,
    safe_execute_pandas,
)
from app.utils.schema import _to_jsonable, infer_dataframe_schema, to_jsonable

__all__ = [
    "_to_jsonable",
    "_validate_sandbox_code",
    "_validate_table_name",
    "ERROR_EXECUTION",
    "ERROR_OK",
    "ERROR_TIMEOUT",
    "SandboxTimeoutError",
    "dataframe_to_pg",
    "drop_table_if_exists",
    "get_table_preview",
    "infer_dataframe_schema",
    "load_table_to_dataframe",
    "safe_execute_pandas",
    "to_jsonable",
]

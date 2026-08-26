"""时间工具：统一的 UTC 时间获取。

历史背景：模型层曾使用 ``datetime.utcnow()``（Python 3.12 已弃用）。
0004 迁移将列统一为 timestamptz 后，默认值改用 aware 的 :func:`utcnow`；
:func:`utcnow_naive` 保留给尚未迁移的存储场景，两者勿混用比较。
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """返回带时区的当前 UTC 时间（tz-aware，配合 timestamptz 列使用）。"""
    return datetime.now(UTC)


def utcnow_naive() -> datetime:
    """返回 naive UTC 当前时间（等价于旧 datetime.utcnow()，无弃用告警）。"""
    return datetime.now(UTC).replace(tzinfo=None)

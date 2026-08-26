"""进度发布工具：Celery worker 调用，通过 Redis publish 推送进度。"""

from typing import Any

import redis

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# 模块级连接池：worker 一次分析要发布 5~6 次进度，
# 复用池化连接避免每次发布都新建/销毁 TCP 连接
_pool: redis.ConnectionPool | None = None


def _get_client() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(settings.redis_url)
    return redis.Redis(connection_pool=_pool)


def publish_progress(
    analysis_id: int,
    stage: str,
    progress: int,
    message: str = "",
    data: dict[str, Any] | None = None,
) -> None:
    """向 Redis `analysis_progress` 频道发布进度消息。

    结构由 ``WSProgressMessage`` schema 统一定义，与前端类型单一事实来源，
    避免手工拼 dict 与 schema 漂移。

    参数:
        analysis_id: 分析任务 ID
        stage: queued / running / succeeded / failed
        progress: 0-100
        message: 人类可读说明
        data: 附加数据（如结果摘要、图表配置）

    容错说明：Redis 不可用时仅记录告警、不抛出——推送失败不应把本可
    成功的分析任务整体打成 failed（终态仍会写入 DB，前端有轮询兜底）。
    """
    from app.schemas.analysis import WSProgressMessage

    payload_model = WSProgressMessage(
        analysis_id=analysis_id,
        stage=stage,
        progress=progress,
        message=message,
        data=data or {},
    )
    try:
        client = _get_client()
        client.publish(
            "analysis_progress",
            payload_model.model_dump_json(),
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "progress.publish_failed",
            extra={"analysis_id": analysis_id, "stage": stage},
            exc_info=True,
        )

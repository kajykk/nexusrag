"""进度发布工具：Celery worker 调用，通过 Redis publish 推送进度。"""

import json

import redis

from app.config import settings


def publish_progress(
    analysis_id: int,
    stage: str,
    progress: int,
    message: str = "",
    data: dict | None = None,
) -> None:
    """向 Redis `analysis_progress` 频道发布进度消息。

    参数:
        analysis_id: 分析任务 ID
        stage: queued / running / succeeded / failed
        progress: 0-100
        message: 人类可读说明
        data: 附加数据（如结果摘要、图表配置）
    """
    client = redis.from_url(settings.redis_url)
    payload = {
        "analysis_id": analysis_id,
        "stage": stage,
        "progress": progress,
        "message": message,
        "data": data or {},
    }
    client.publish("analysis_progress", json.dumps(payload, ensure_ascii=False))
    client.close()

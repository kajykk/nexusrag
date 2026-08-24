"""WebSocket 连接管理器。

负责维护前端连接，并通过 Redis pub/sub 接收 Celery worker
推送的分析进度，转发给订阅了对应 analysis_id 的客户端。
"""

import json

from fastapi import WebSocket

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """内存连接池 + Redis 订阅转发。"""

    def __init__(self) -> None:
        # analysis_id -> set[WebSocket]
        self._subscriptions: dict[int, set[WebSocket]] = {}

    # ---- 连接管理 ----
    async def connect(self, websocket: WebSocket, analysis_id: int) -> None:
        await websocket.accept()
        self._subscriptions.setdefault(analysis_id, set()).add(websocket)
        logger.info(
            "ws.connected", extra={"analysis_id": analysis_id, "subscribers": len(self._subscriptions[analysis_id])}
        )

    def disconnect(self, websocket: WebSocket, analysis_id: int) -> None:
        subs = self._subscriptions.get(analysis_id)
        if subs and websocket in subs:
            subs.remove(websocket)
            if not subs:
                self._subscriptions.pop(analysis_id, None)

    async def send_to_subscribers(self, analysis_id: int, message: dict) -> None:
        """向订阅了某 analysis_id 的所有客户端广播消息。"""
        subs = self._subscriptions.get(analysis_id, set()).copy()
        dead: list[WebSocket] = []
        for ws in subs:
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001
                logger.warning("ws.send_failed", extra={"analysis_id": analysis_id}, exc_info=True)
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, analysis_id)


manager = ConnectionManager()


async def redis_subscriber_loop() -> None:
    """后台任务：订阅 Redis 的 `analysis_progress` 频道，
    将收到的进度消息转发给对应的 WebSocket 客户端。
    """
    import redis.asyncio as aioredis

    redis = aioredis.from_url(settings.redis_url)
    pubsub = redis.pubsub()
    await pubsub.subscribe("analysis_progress")
    logger.info("ws.redis_subscribed", extra={"channel": "analysis_progress"})
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                payload = json.loads(message["data"])
                analysis_id = int(payload.get("analysis_id", 0))
                await manager.send_to_subscribers(analysis_id, payload)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "ws.forward_failed",
                    extra={"error": str(exc), "channel": "analysis_progress"},
                    exc_info=True,
                )
    finally:
        await pubsub.unsubscribe("analysis_progress")
        await redis.close()
        logger.info("ws.redis_unsubscribed", extra={"channel": "analysis_progress"})

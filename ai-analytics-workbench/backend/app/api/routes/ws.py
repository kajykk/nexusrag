"""WebSocket 路由：实时推送分析进度（需 JWT 认证 + 归属校验）。

鉴权方式：浏览器 WebSocket 无法自定义请求头，客户端通过查询参数携带 token：
    ws://host/ws/analysis/{analysis_id}?token=<access_token>
连接建立前完成校验，未通过则以 4401/4403 关闭。
"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.db.session import SessionLocal
from app.logging_config import get_logger
from app.models import Analysis, User
from app.security import decode_token
from app.services.ownership import is_visible
from app.ws.manager import manager

logger = get_logger(__name__)

router = APIRouter(tags=["ws"])


def _authenticate(token: str) -> User | None:
    """解析 JWT 并返回有效用户；失败返回 None。"""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access" or not payload.get("sub"):
        return None
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        return user
    finally:
        db.close()


@router.websocket("/ws/analysis/{analysis_id}")
async def analysis_ws(websocket: WebSocket, analysis_id: int, token: str = Query(default="")) -> None:
    """订阅指定分析任务的实时进度。

    客户端连接 `ws://host/ws/analysis/{analysis_id}?token=<jwt>` 后，
    会收到该任务的 queued/running/succeeded/failed 进度消息。

    安全：必须携带有效 JWT，且该分析任务对当前用户可见，
    否则拒绝连接（401 未认证 / 403 无权访问该任务）。
    """
    # 1. 校验 JWT
    user = _authenticate(token)
    if user is None:
        await websocket.close(code=4401, reason="unauthorized")
        logger.warning("ws.unauthorized", extra={"analysis_id": analysis_id})
        return

    # 2. 校验分析任务归属（不可见视为不存在）
    db = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        allowed = analysis is not None and is_visible(analysis, user)
    finally:
        db.close()

    if not allowed:
        await websocket.close(code=4403, reason="forbidden")
        logger.warning("ws.forbidden", extra={"analysis_id": analysis_id, "user_id": user.id})
        return

    await manager.connect(websocket, analysis_id)
    try:
        # 发送连接确认
        await websocket.send_json(
            {
                "analysis_id": analysis_id,
                "stage": "connected",
                "progress": 0,
                "message": "已连接到进度推送频道",
            }
        )
        # 保持连接，等待消息
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, analysis_id)

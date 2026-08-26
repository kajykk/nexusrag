"""WebSocket 路由：实时推送分析进度（需 JWT 认证 + 归属校验）。

挂载在应用根路径（``/ws/analysis/{analysis_id}``），与前端连接地址
及 vite 代理约定一致；鉴权方式：浏览器 WebSocket 无法自定义请求头，
客户端通过查询参数携带 token：
    ws://host/ws/analysis/{analysis_id}?token=<access_token>
连接建立前完成校验，未通过则以 4401/4403 关闭。

数据库会话经 FastAPI 依赖注入获取（与 HTTP 路由共用 get_db 覆盖点），
测试夹具可统一替换。
"""

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.logging_config import get_logger
from app.models import Analysis, User
from app.security import decode_token
from app.services.ownership import is_visible
from app.ws.manager import manager

logger = get_logger(__name__)

router = APIRouter(tags=["ws"])


def _authenticate(token: str, db: Session) -> User | None:
    """解析 JWT 并返回有效用户；失败返回 None。"""
    payload = decode_token(token, expected_type="access")
    if not payload or not payload.get("sub"):
        return None
    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


@router.websocket("/ws/analysis/{analysis_id}")
async def analysis_ws(
    websocket: WebSocket,
    analysis_id: int,
    token: str = Query(default=""),
    db: Session = Depends(get_session),
) -> None:
    """订阅指定分析任务的实时进度。

    客户端连接 `ws://host/ws/analysis/{analysis_id}?token=<jwt>` 后，
    会收到该任务的 queued/running/succeeded/failed 进度消息。

    安全：必须携带有效 JWT（type=access），且该分析任务对当前用户可见，
    否则拒绝连接。注意：先 accept 再以自定义关闭码关闭——
    Starlette 在未 accept 时 close() 会退化为 HTTP 403，
    客户端拿不到约定的 4401/4403 关闭码。
    """
    # 1. 校验 JWT
    user = _authenticate(token, db)
    if user is None:
        await websocket.accept()
        await websocket.close(code=4401, reason="unauthorized")
        logger.warning("ws.unauthorized", extra={"analysis_id": analysis_id})
        return

    # 2. 校验分析任务归属（不可见视为不存在）
    analysis = db.get(Analysis, analysis_id)
    allowed = analysis is not None and is_visible(analysis, user)

    if not allowed:
        await websocket.accept()
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
        pass
    finally:
        # 兜底清理：非 Disconnect 类异常（协议错误等）也必须移除订阅，防泄漏
        manager.disconnect(websocket, analysis_id)

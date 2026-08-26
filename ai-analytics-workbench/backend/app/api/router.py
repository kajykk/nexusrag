"""路由聚合：注册所有子路由。

注意：ws.router 不在此处注册——WebSocket 挂在应用根路径
（``/ws/analysis/{id}``），与前端连接地址及 vite 代理约定一致；
放在 /api/v1 前缀下会导致前端连接 404、进度推送静默失效。
"""

from fastapi import APIRouter

from app.api.routes import analysis, auth, datasets, health, reports

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(datasets.router)
api_router.include_router(analysis.router)
api_router.include_router(reports.router)

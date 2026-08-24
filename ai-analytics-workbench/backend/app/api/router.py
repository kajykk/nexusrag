"""路由聚合：注册所有子路由。"""

from fastapi import APIRouter

from app.api.routes import analysis, auth, datasets, health, reports, ws

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(datasets.router)
api_router.include_router(analysis.router)
api_router.include_router(reports.router)
api_router.include_router(ws.router)

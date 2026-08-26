"""FastAPI 应用入口。"""

import asyncio
import contextlib
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app as app_package
from app.api.router import api_router
from app.config import settings
from app.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

# 启动时配置 logging（必须在任何业务模块 import 之前）
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时清理过期图表并开启 Redis 订阅后台任务。"""
    import contextlib as _contextlib

    from app.visualization import cleanup_old_charts
    from app.ws.manager import redis_subscriber_loop

    # 启动期回收过期工件（尽力而为，失败不阻断启动）
    with _contextlib.suppress(Exception):
        removed = cleanup_old_charts(settings.CHART_RETENTION_DAYS)
        if removed:
            logger.info("charts.cleanup_done", extra={"removed": removed})

    task = asyncio.create_task(redis_subscriber_loop())
    yield
    task.cancel()
    # 等待取消完成并吞掉 CancelledError，避免关停日志噪音
    with contextlib.suppress(asyncio.CancelledError):
        await task


app = FastAPI(
    title="AI 数据分析工作台",
    description="通过自然语言对话完成数据分析、可视化与报告生成的全栈平台",
    version=app_package.__version__,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)

# 工件目录（由 Celery worker / API 写入）。安全说明：不再公开挂载静态目录——
# 图表与 PDF 一度可被任意匿名遍历下载（IDOR），现统一经认证路由下发：
#   - PDF:  GET /api/v1/reports/{id}/download
#   - 图表: GET /api/v1/analyses/{id}/chart
os.makedirs(settings.reports_abs_dir, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# 路由（REST 挂 /api/v1；WebSocket 挂根路径，见 api/router.py 说明）
app.include_router(api_router, prefix="/api/v1")
from app.api.routes.ws import router as ws_router  # noqa: E402

app.include_router(ws_router)


@app.get("/")
def root() -> dict:
    return {
        "name": "AI 数据分析工作台",
        "version": "0.1.0",
        "docs": "/docs",
        "api": "/api/v1",
    }

"""健康检查路由。"""

from fastapi import APIRouter

import app
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """健康检查端点（版本号统一取 app.__version__）。"""
    logger.info("health.check")
    return {"status": "ok", "service": "ai-analytics-workbench", "version": app.__version__}

"""FastAPI 应用入口。"""

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import settings
from app.logging_config import setup_logging

# 启动时配置 logging（必须在任何业务模块 import 之前）
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时开启 Redis 订阅后台任务。"""
    from app.ws.manager import redis_subscriber_loop

    task = asyncio.create_task(redis_subscriber_loop())
    yield
    task.cancel()


app = FastAPI(
    title="AI 数据分析工作台",
    description="通过自然语言对话完成数据分析、可视化与报告生成的全栈平台",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件：图表图片、报告
os.makedirs("reports", exist_ok=True)
os.makedirs("uploads", exist_ok=True)
app.mount("/reports", StaticFiles(directory="reports"), name="reports")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root() -> dict:
    return {
        "name": "AI 数据分析工作台",
        "version": "0.1.0",
        "docs": "/docs",
        "api": "/api/v1",
    }

"""Celery 应用：用于异步执行数据分析任务。"""

from celery import Celery

from app.config import settings
from app.logging_config import setup_logging

# worker 进程启动时初始化日志配置
setup_logging()

celery_app = Celery(
    "ai_analytics_workbench",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.services.analysis_service"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    # 可靠性：执行完成才确认消息；worker 被 OOM/重启杀死时任务重投，
    # 避免任务永久卡在 running。配合 execute_analysis 入口的幂等检查。
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


@celery_app.task(name="run_analysis_task")
def run_analysis_task(analysis_id: int) -> dict:
    """异步执行分析任务（Celery 入口）。

    在 worker 进程中调用 analysis_service 的同步实现，
    通过 Redis pub/sub 推送进度，WebSocket 侧再转发给前端。
    """
    from app.services.analysis_service import execute_analysis

    return execute_analysis(analysis_id)

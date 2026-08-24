"""数据库初始化脚本：创建所有表。

可被 docker-compose 启动命令调用，也可手动执行：
    python -m app.db.init_db
"""

from app.db.session import Base, engine
from app.logging_config import get_logger
from app.models import analysis, dataset  # noqa: F401  确保模型被注册

logger = get_logger(__name__)


def init_db() -> None:
    """创建所有数据表（开发环境使用，生产环境走 Alembic 迁移）。"""
    Base.metadata.create_all(bind=engine)
    logger.info("db.init_complete", extra={"engine": str(engine.url)})


if __name__ == "__main__":
    init_db()

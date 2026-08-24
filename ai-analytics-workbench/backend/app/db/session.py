"""数据库会话与 Base 模型。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


def _build_engine():
    """构造 SQLAlchemy 引擎：SQLite 与其他 DB 使用不同的 pool 配置。"""
    url = settings.DATABASE_URL
    is_sqlite = url.startswith("sqlite")
    kwargs: dict = {
        "pool_pre_ping": True,
        "echo": settings.APP_DEBUG and settings.APP_ENV == "development",
    }
    # SQLite 的 SingletonThreadPool 不支持 pool_size/max_overflow
    if not is_sqlite:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
    return create_engine(url, **kwargs)


# 同步引擎（数据分析场景以同步为主，配合 Celery 异步任务）
engine = _build_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""

    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供数据库会话并自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

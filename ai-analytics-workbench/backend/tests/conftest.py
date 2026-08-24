"""pytest 全局夹具（P0 新增）。"""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 确保 backend/ 在 sys.path 中
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

# 测试环境变量（在导入 app 之前设置）
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_DEBUG", "false")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")


from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Analysis, Dataset, Report, User  # noqa: E402,F401 确保模型被注册
from app.security import create_access_token, hash_password  # noqa: E402


@pytest.fixture(scope="function")
def db_engine():
    """每个测试用例使用独立的内存 SQLite 数据库。"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """事务级数据库会话，测试结束自动回滚。"""
    testing_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = testing_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """带数据库覆盖的 FastAPI TestClient。"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db_session):
    """工厂夹具：创建测试用户。"""

    def _make(
        email: str = "test@example.com", password: str = "password123", name: str = "Test User", is_admin: bool = False
    ) -> User:
        user = User(
            email=email,
            name=name,
            hashed_password=hash_password(password),
            is_admin=is_admin,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture
def auth_token(make_user):
    """已登录用户的 JWT token。"""
    user = make_user()
    return create_access_token(subject=user.id), user


@pytest.fixture
def auth_headers(auth_token):
    """带 Authorization 的请求头。"""
    token, _ = auth_token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_dataset(db_session):
    """工厂夹具：创建测试数据集元数据。每次调用生成唯一的 table_name。"""
    import secrets
    import time

    counter = {"n": 0}

    def _make(**kwargs) -> Dataset:
        counter["n"] += 1
        unique_suffix = f"{int(time.time() * 1000)}_{counter['n']}_{secrets.token_hex(3)}"
        defaults = {
            "name": "测试数据集",
            "original_filename": "test.csv",
            "table_name": f"ds_test_{unique_suffix}",
            "file_type": "csv",
            "row_count": 100,
            "column_count": 5,
            "columns_schema": "[]",
            "description": "",
        }
        defaults.update(kwargs)
        dataset = Dataset(**defaults)
        db_session.add(dataset)
        db_session.commit()
        db_session.refresh(dataset)
        return dataset

    return _make

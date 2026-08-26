"""应用配置：通过环境变量注入，支持 .env 文件。"""

from functools import lru_cache
from urllib.parse import quote

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 弱默认密钥，仅在非生产环境使用
_WEAK_SECRET_DEFAULT = "change-me-in-production"
# 弱默认数据库口令，仅在非生产环境使用
_WEAK_DB_URL_MARKER = "analytics:analytics123"


class Settings(BaseSettings):
    """全局配置项。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用
    APP_ENV: str = "development"
    # 默认关闭：开发态回显 SQL 会把参数值（可能含敏感数据）写进日志
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = _WEAK_SECRET_DEFAULT

    # 日志（P1 新增）
    LOG_LEVEL: str = "INFO"  # DEBUG / INFO / WARNING / ERROR / CRITICAL
    LOG_JSON: bool = False  # 生产环境推荐 true，便于 ELK/Loki 采集

    # JWT 认证（P0 新增）
    JWT_ALGORITHM: str = "HS256"
    # 默认 12 小时：过长的 token 一旦泄漏无法撤销；如需更长会话请实现 refresh 机制
    JWT_EXPIRE_MINUTES: int = 60 * 12
    # refresh token 有效期（配合 /auth/refresh 端点使用）
    JWT_REFRESH_EXPIRE_MINUTES: int = 60 * 24 * 7
    JWT_TOKEN_URL: str = "/api/v1/auth/login"

    # 演示账号是否授予管理员权限（默认 false，降权防滥用；仅演示环境显式开启）
    DEMO_ALLOW_ADMIN: bool = False

    # 数据库
    DATABASE_URL: str = "postgresql+psycopg://analytics:analytics123@localhost:5432/analytics_workbench"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # LLM
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"

    # 上传
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "./uploads"

    # 报告/图表工件目录：API 进程与 Celery worker 必须指向同一绝对路径，
    # 否则 DB 中的相对路径会因读取者工作目录不同而错位
    REPORTS_DIR: str = "./reports"
    # 图表保留天数：启动清理超过该天数的 chart_*.png；0 表示禁用清理
    CHART_RETENTION_DAYS: int = 30

    # 沙箱（进程级/容器级隔离执行用户分析代码）
    SANDBOX_TIMEOUT_SECONDS: int = 30  # 墙钟超时，超时击杀整个进程树（两种模式通用）
    SANDBOX_MODE: str = "subprocess"  # subprocess（默认）| docker
    SANDBOX_DOCKER_IMAGE: str = "python:3.12-alpine"  # docker 模式镜像；缺失时自动 pull

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @field_validator("CORS_ORIGINS")
    @classmethod
    def normalize_cors(cls, v: str) -> str:
        return v.strip()

    @field_validator("SANDBOX_MODE")
    @classmethod
    def validate_sandbox_mode(cls, v: str) -> str:
        mode = v.strip().lower()
        if mode not in ("subprocess", "docker"):
            raise ValueError(f"SANDBOX_MODE 仅支持 subprocess / docker，收到: {v!r}")
        return mode

    @model_validator(mode="after")
    def _enforce_production_secret(self) -> "Settings":
        """生产环境必须显式设置非弱 SECRET_KEY / DATABASE_URL。"""
        if self.APP_ENV == "production":
            if not self.SECRET_KEY or self.SECRET_KEY == _WEAK_SECRET_DEFAULT:
                raise ValueError(
                    "生产环境（APP_ENV=production）必须通过环境变量 SECRET_KEY " "设置一个高强度密钥，禁止使用默认值。"
                )
            if _WEAK_DB_URL_MARKER in self.DATABASE_URL:
                raise ValueError(
                    "生产环境（APP_ENV=production）禁止使用默认弱口令数据库连接串，"
                    "请通过环境变量 DATABASE_URL 配置真实凭据。"
                )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def redis_url(self) -> str:
        # 密码需 URL 编码：含 @ : / # 等字符时未编码的拼接会产生错误解析
        auth = f":{quote(self.REDIS_PASSWORD, safe='')}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def reports_abs_dir(self) -> str:
        """reports 目录绝对路径（唯一事实来源）。"""
        import os

        return os.path.abspath(self.REPORTS_DIR)


@lru_cache
def get_settings() -> Settings:
    """单例配置，避免重复读取环境变量。"""
    return Settings()


settings = get_settings()

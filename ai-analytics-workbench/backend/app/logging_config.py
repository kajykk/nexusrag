"""统一日志配置（P1 新增）。

设计目标：
- 开发环境：人类可读的单行格式（时间 / 级别 / logger / 消息）
- 生产环境（LOG_JSON=true）：单行 JSON，便于 ELK / Loki / CloudWatch 采集
- 第三方库噪音（uvicorn.access、sqlalchemy.engine、markdown）按级别静音
- 一次配置全局生效，幂等可重复调用

使用方式：
    from app.logging_config import setup_logging
    setup_logging()
"""

from __future__ import annotations

import json
import logging
import logging.config
import sys
from datetime import UTC, datetime
from typing import Any

# 已知的第三方噪音 logger，统一上抬到 WARNING 级别
_NOISY_LOGGERS = (
    "uvicorn.access",
    "sqlalchemy.engine",
    "markdown",
    "httpx",
    "httpcore",
    "openai",
    "celery.worker.strategy",
)

# 已知配置过就会阻塞输出的"已初始化"标记
_SETUP_DONE_ATTR = "_app_logging_configured"

# LogRecord 保留属性集合：由标准库属性自动推导，避免手工清单漏掉
# 新版本新增字段（如 3.12 的 taskName）被误当作 extra 输出
_RESERVED_ATTRS: frozenset[str] = frozenset(
    vars(logging.LogRecord("name", 0, "path", 1, "msg", (), None)).keys()
) | {"message", "asctime", "taskName"}


class SingleLineFormatter(logging.Formatter):
    """人类可读格式，消息中的换行转义为字面 \\n。

    用户可控内容（email/question 等）含换行时可伪造日志行，
    单行化是结构化采集的基本前提。
    """

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        return text.replace("\r", "\\r").replace("\n", "\\n")


class JsonFormatter(logging.Formatter):
    """单行 JSON 日志格式器。

    输出字段：ts / level / logger / message / module / line / func
    以及 record.extra（如 exc_info 会以 exc 字段输出）。
    """

    def format(self, record: logging.LogRecord) -> str:
        # 时间统一 UTC + ISO8601 毫秒
        ts = datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds")
        payload: dict[str, Any] = {
            "ts": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
            "func": record.funcName,
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # 额外字段（如 logger.info(..., extra={"trace_id": ...})）
        for k, v in record.__dict__.items():
            if k in _RESERVED_ATTRS or k.startswith("_"):
                continue
            payload.setdefault(k, _safe_jsonable(v))
        return json.dumps(payload, ensure_ascii=False, default=str, allow_nan=False)


def _safe_jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _human_formatter() -> logging.Formatter:
    return SingleLineFormatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_logging() -> None:
    """初始化全局 logging 配置。幂等：重复调用不会重复添加 handler。"""
    root = logging.getLogger()
    if getattr(root, _SETUP_DONE_ATTR, False):
        # 仅在级别变化时更新阈值
        from app.config import settings

        root.setLevel(settings.LOG_LEVEL.upper())
        for name in _NOISY_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)
        return

    from app.config import settings

    handlers: dict[str, dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "json" if settings.LOG_JSON else "human",
        }
    }
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "human": {"()": lambda: _human_formatter()},
                "json": {"()": lambda: JsonFormatter()},
            },
            "handlers": handlers,
            "loggers": {name: {"level": "WARNING"} for name in _NOISY_LOGGERS},
            "root": {
                "level": settings.LOG_LEVEL.upper(),
                "handlers": ["console"],
            },
        }
    )
    setattr(root, _SETUP_DONE_ATTR, True)


def get_logger(name: str) -> logging.Logger:
    """获取 logger，确保全局配置已初始化。"""
    setup_logging()
    return logging.getLogger(name)

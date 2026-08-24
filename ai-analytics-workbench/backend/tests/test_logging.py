"""logging_config 模块测试（P1 新增）。"""

import json
import logging

from app.logging_config import JsonFormatter, get_logger, setup_logging


class TestJsonFormatter:
    def test_basic_fields_present(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=42,
            msg="hello %s",
            args=("world",),
            exc_info=None,
        )
        out = formatter.format(record)
        payload = json.loads(out)
        assert payload["level"] == "INFO"
        assert payload["logger"] == "test.logger"
        assert payload["message"] == "hello world"
        assert payload["line"] == 42
        assert payload["module"]
        assert "ts" in payload

    def test_exception_field_included_when_exc_info(self):
        formatter = JsonFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys as _sys

            exc_info = _sys.exc_info()
        record = logging.LogRecord(
            name="x",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="failed",
            args=(),
            exc_info=exc_info,
        )
        payload = json.loads(formatter.format(record))
        assert "exc" in payload
        assert "ValueError" in payload["exc"]
        assert "boom" in payload["exc"]

    def test_extra_fields_propagated(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="x",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="m",
            args=(),
            exc_info=None,
        )
        record.trace_id = "abc-123"
        record.user_id = 7
        record._private = "hidden"
        payload = json.loads(formatter.format(record))
        assert payload["trace_id"] == "abc-123"
        assert payload["user_id"] == 7
        assert "_private" not in payload

    def test_non_jsonable_extra_falls_back_to_str(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="x",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="m",
            args=(),
            exc_info=None,
        )

        class NotSerializable:
            def __repr__(self) -> str:
                return "<NotSerializable>"

        record.obj = NotSerializable()
        payload = json.loads(formatter.format(record))
        assert "obj" in payload
        assert isinstance(payload["obj"], str)

    def test_chinese_message_kept_as_utf8(self):
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="x",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="分析失败: %s",
            args=("数据集不存在",),
            exc_info=None,
        )
        out = formatter.format(record)
        # 应能被 json.loads 解析，且中文字符原样保留（不转 \uXXXX）
        assert "分析失败" in out
        assert "数据集不存在" in out


class TestSetupLogging:
    def test_setup_logging_is_idempotent(self):
        """重复调用不应重复添加 handler。"""
        root1 = logging.getLogger()
        setup_logging()
        handlers_after_first = len(root1.handlers)
        setup_logging()
        handlers_after_second = len(root1.handlers)
        assert handlers_after_first == handlers_after_second

    def test_get_logger_returns_named_logger(self):
        logger = get_logger("my.module")
        assert logger.name == "my.module"
        assert isinstance(logger, logging.Logger)

    def test_log_level_updated_when_settings_change(self, monkeypatch):
        """第二次调用时根据 settings.LOG_LEVEL 更新 root 级别。"""
        from app.config import settings

        monkeypatch.setattr(settings, "LOG_LEVEL", "ERROR")
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.ERROR

    def test_noisy_loggers_set_to_warning(self):
        setup_logging()
        for name in ("uvicorn.access", "sqlalchemy.engine", "markdown", "httpx", "httpcore", "openai"):
            assert logging.getLogger(name).level == logging.WARNING


class TestHumanFormatterIntegration:
    """端到端：logging 输出能被 pytest 截获。"""

    def test_human_format_single_line(self, caplog):
        setup_logging()
        logger = get_logger("test.integration")
        # caplog 默认是 propagation；确保级别足够低能被捕获
        with caplog.at_level(logging.WARNING, logger="test.integration"):
            logger.warning("test-event")
        # 至少应捕获到一条 WARNING 记录
        records = [r for r in caplog.records if r.name == "test.integration" and r.levelname == "WARNING"]
        assert records
        assert records[0].getMessage() == "test-event"

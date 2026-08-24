"""utils.db 模块测试：表名校验与 SQL 注入防御（P1-3 新增）。"""

import pytest

from app.utils import _validate_table_name
from app.utils.db import drop_table_if_exists, get_table_preview


class TestValidateTableName:
    """表名严格校验：仅允许 PostgreSQL 合法标识符。"""

    @pytest.mark.parametrize(
        "name",
        [
            "ds_1_abc",
            "my_table",
            "_private",
            "Table_With_Underscores",
            "a",
            "A1",
            "x" * 63,  # 最长 63 字节
        ],
    )
    def test_valid_names(self, name):
        # 不抛异常即通过
        _validate_table_name(name)

    @pytest.mark.parametrize(
        "name",
        [
            "",  # 空字符串
            "1table",  # 数字开头
            "table-name",  # 含连字符
            "table name",  # 含空格
            "table;",  # 含分号
            'table"; DROP TABLE users; --',  # 经典 SQL 注入
            "table' OR '1'='1",  # 单引号注入
            "table$special",  # 特殊字符
            "x" * 64,  # 超长
            None,  # None
            123,  # 非字符串
            ["list"],  # 非字符串
        ],
    )
    def test_invalid_names_raise(self, name):
        with pytest.raises(ValueError, match="非法表名"):
            _validate_table_name(name)


class TestGetTablePreviewSqlInjection:
    """get_table_preview 必须拒绝 SQL 注入式表名。"""

    def test_injection_attempt_raises(self):
        with pytest.raises(ValueError, match="非法表名"):
            get_table_preview('users"; DROP TABLE users; --')

    def test_non_string_raises(self):
        with pytest.raises(ValueError, match="非法表名"):
            get_table_preview(None)  # type: ignore[arg-type]

    def test_invalid_limit_raises(self):
        with pytest.raises(ValueError, match="非法 limit"):
            get_table_preview("ds_1_abc", limit=-1)

        with pytest.raises(ValueError, match="非法 limit"):
            get_table_preview("ds_1_abc", limit=10001)

        with pytest.raises(ValueError, match="非法 limit"):
            get_table_preview("ds_1_abc", limit="5")  # type: ignore[arg-type]


class TestDropTableIfExistsSqlInjection:
    """drop_table_if_exists 必须拒绝 SQL 注入式表名。"""

    def test_injection_attempt_raises(self):
        with pytest.raises(ValueError, match="非法表名"):
            drop_table_if_exists('users"; DROP TABLE users; --')

    def test_semicolon_injection_raises(self):
        with pytest.raises(ValueError, match="非法表名"):
            drop_table_if_exists("users; DROP TABLE users")

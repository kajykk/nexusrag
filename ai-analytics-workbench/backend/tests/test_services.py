"""services 模块测试（P0 新增）。

只测纯函数与可单元测试的部分，不依赖真实 PG 表的 service 函数
（如 upload_dataset 需要 dataframe_to_pg 调用真实 PG）。
"""

import pytest

from app.services.report_service import (
    _dict_to_markdown,
    _format_result,
    _list_to_markdown_table,
    _table_to_markdown,
)


class TestFormatResult:
    def test_none(self):
        assert _format_result(None) == "（无结果）"

    def test_scalar_string(self):
        result = _format_result("hello")
        assert "```" in result
        assert "hello" in result

    def test_dict_of_lists(self):
        """{col: [values]} 形式应转为表格。"""
        result = _format_result({"name": ["A", "B"], "age": [10, 20]})
        assert "| name" in result
        assert "| age" in result
        assert "| A" in result
        assert "| 20" in result

    def test_dict_of_scalars(self):
        """{key: scalar} 形式应转为键值列表。"""
        result = _format_result({"total": 100, "count": 5})
        assert "- **total**: 100" in result
        assert "- **count**: 5" in result

    def test_list_of_dicts(self):
        result = _format_result([{"name": "A", "score": 90}, {"name": "B", "score": 80}])
        assert "| name" in result
        assert "| A" in result
        assert "| B" in result
        assert "90" in result

    def test_list_of_dicts_truncated_to_50(self):
        items = [{"id": i} for i in range(100)]
        result = _format_result(items)
        # 只显示前 50 行
        assert "| 0 |" in result
        assert "| 49 |" in result
        assert "| 99 |" not in result


class TestListToMarkdownTable:
    def test_empty(self):
        assert _list_to_markdown_table([]) == "（空）"

    def test_single_row(self):
        result = _list_to_markdown_table([{"a": 1, "b": 2}])
        lines = result.split("\n")
        assert len(lines) == 3  # header + sep + 1 row
        assert "| a | b |" in lines[0]

    def test_column_order_preserved(self):
        result = _list_to_markdown_table([{"x": 1, "y": 2, "z": 3}])
        assert result.index("x") < result.index("y") < result.index("z")


class TestTableToMarkdown:
    def test_basic(self):
        result = _table_to_markdown(["a", "b"], [(1, 2), (3, 4)])
        assert "| a | b |" in result
        assert "| 1 | 2 |" in result
        assert "| 3 | 4 |" in result

    def test_truncated(self):
        cols = ["v"]
        rows = [(i,) for i in range(100)]
        result = _table_to_markdown(cols, rows)
        # 只显示前 50 行
        assert "| 0 |" in result
        assert "| 49 |" in result
        assert "| 99 |" not in result


class TestDictToMarkdown:
    def test_basic(self):
        result = _dict_to_markdown({"a": 1, "b": "hello"})
        assert "- **a**: 1" in result
        assert "- **b**: hello" in result

    def test_empty(self):
        assert _dict_to_markdown({}) == ""


class TestDatasetServiceHelpers:
    """dataset_service 的纯函数（_generate_table_name 等）。"""

    def test_table_name_format(self):
        from app.services.dataset_service import _generate_table_name

        name = _generate_table_name(42)
        assert name.startswith("ds_42_")
        # 后缀应为 6 位 hex 字符
        suffix = name.rsplit("_", 1)[-1]
        assert len(suffix) == 6
        int(suffix, 16)  # 必须是有效 hex

    def test_table_name_uniqueness(self):
        from app.services.dataset_service import _generate_table_name

        names = {_generate_table_name(1) for _ in range(20)}
        # 高概率所有都不同（6 位 hex = 16M 种可能）
        assert len(names) == 20


class TestAnalysisService:
    """analysis_service 的 create_analysis 与 list_analyses 可独立测试。"""

    def test_create_analysis_unknown_dataset(self, db_session):
        from app.services.analysis_service import create_analysis

        with pytest.raises(ValueError, match="数据集.*不存在"):
            create_analysis(db_session, dataset_id=9999, question="测试")

    def test_create_analysis_success(self, db_session, make_dataset):
        from app.models import Analysis
        from app.services.analysis_service import create_analysis

        ds = make_dataset()
        analysis = create_analysis(db_session, ds.id, "总销售额多少")
        assert analysis.id is not None
        assert analysis.status == "pending"
        assert analysis.question == "总销售额多少"
        assert analysis.dataset_id == ds.id

        # 从数据库查询
        from sqlalchemy import select

        stmt = select(Analysis).where(Analysis.id == analysis.id)
        saved = db_session.execute(stmt).scalar_one()
        assert saved.question == "总销售额多少"

    def test_list_analyses_with_filter(self, db_session, make_dataset):
        from app.services.analysis_service import create_analysis, list_analyses

        ds1 = make_dataset(name="DS1")
        ds2 = make_dataset(name="DS2")

        create_analysis(db_session, ds1.id, "q1")
        create_analysis(db_session, ds1.id, "q2")
        create_analysis(db_session, ds2.id, "q3")

        # 过滤 ds1
        items = list_analyses(db_session, dataset_id=ds1.id)
        assert len(items) == 2
        for a in items:
            assert a.dataset_id == ds1.id

        # 不过滤：全部
        all_items = list_analyses(db_session)
        assert len(all_items) == 3

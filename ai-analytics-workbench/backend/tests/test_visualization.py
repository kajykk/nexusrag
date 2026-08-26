"""可视化模块测试：_to_dataframe 与 render_chart。"""

import os

import pandas as pd

from app.visualization.matplotlib_charts import _to_dataframe, render_chart


class TestToDataframe:
    def test_to_dataframe_from_dict(self):
        """测试 dict 转 DataFrame。"""
        result = _to_dataframe({"a": [1, 2], "b": [3, 4]})
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["a", "b"]
        assert len(result) == 2

    def test_to_dataframe_from_dict_scalar(self):
        """测试标量值 dict 转单行 DataFrame。"""
        result = _to_dataframe({"a": 1, "b": 2})
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["a"] == 1

    def test_to_dataframe_from_list(self):
        """测试 list 转 DataFrame。"""
        result = _to_dataframe([{"a": 1}, {"a": 2}])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ["a"]

    def test_to_dataframe_from_list_of_scalars(self):
        """测试标量 list 转 DataFrame。"""
        result = _to_dataframe([1, 2, 3])
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["value"]
        assert len(result) == 3

    def test_to_dataframe_from_empty_list(self):
        """测试空 list 转 DataFrame。"""
        result = _to_dataframe([])
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_to_dataframe_from_none(self):
        """测试 None 返回 None。"""
        result = _to_dataframe(None)
        assert result is None

    def test_to_dataframe_from_dataframe(self):
        """测试 DataFrame 原样返回。"""
        df = pd.DataFrame({"a": [1, 2]})
        result = _to_dataframe(df)
        assert result is df


class TestRenderChart:
    def test_render_chart_table(self, tmp_path, monkeypatch):
        """测试 table 类型渲染生成 PNG 文件（文件名带时间戳后缀防覆盖）。"""
        monkeypatch.chdir(tmp_path)
        result = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        path = render_chart(result, "table", analysis_id=1)
        assert path.startswith("reports/chart_1_")
        assert path.endswith(".png")
        assert os.path.exists(path)
        # 验证是 PNG 文件
        with open(path, "rb") as f:
            header = f.read(8)
        assert header.startswith(b"\x89PNG")

    def test_render_chart_bar(self, tmp_path, monkeypatch):
        """测试 bar 类型渲染生成 PNG 文件。"""
        monkeypatch.chdir(tmp_path)
        result = {"category": ["A", "B", "C"], "value": [10, 20, 30]}
        path = render_chart(result, "bar", analysis_id=2, chart_config={"title": "柱状图"})
        assert path.startswith("reports/chart_2_")
        assert os.path.exists(path)
        with open(path, "rb") as f:
            header = f.read(8)
        assert header.startswith(b"\x89PNG")

    def test_render_chart_none_result(self, tmp_path, monkeypatch):
        """测试 result 为 None 时仍生成文件（table 降级）。"""
        monkeypatch.chdir(tmp_path)
        path = render_chart(None, "table", analysis_id=3)
        assert os.path.exists(path)

    def test_render_chart_unknown_type_falls_back_to_table(self, tmp_path, monkeypatch):
        """测试未知 chart_type 降级为 table。"""
        monkeypatch.chdir(tmp_path)
        result = [{"a": 1}]
        path = render_chart(result, "unknown_type", analysis_id=4)
        assert os.path.exists(path)

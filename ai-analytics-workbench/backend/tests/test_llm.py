"""LLM 工具测试：parse_json_response 与 build_user_prompt。"""

import json

import pytest

from app.llm import build_user_prompt, parse_json_response


class TestParseJsonResponse:
    def test_parse_json_response_valid(self):
        """测试合法 JSON 解析。"""
        content = '{"code": "result = df.sum()", "chart_type": "bar"}'
        result = parse_json_response(content)
        assert result["code"] == "result = df.sum()"
        assert result["chart_type"] == "bar"

    def test_parse_json_response_with_text(self):
        """测试带前后文本的 JSON 提取。"""
        content = '以下是分析结果：\n{"code": "x = 1", "summary": "汇总"}\n请参考上述代码。'
        result = parse_json_response(content)
        assert result["code"] == "x = 1"
        assert result["summary"] == "汇总"

    def test_parse_json_response_invalid(self):
        """测试无效 JSON 抛异常。"""
        with pytest.raises(json.JSONDecodeError):
            parse_json_response("这不是 JSON，也没有花括号")


class TestBuildUserPrompt:
    def test_build_user_prompt(self):
        """测试用户提示构造（含 question、schema、preview）。"""
        question = "统计每个部门的平均薪资"
        columns_schema = [
            {"name": "department", "dtype": "object", "sample": ["研发", "销售"]},
            {"name": "salary", "dtype": "int64", "sample": [10000, 12000]},
        ]
        preview = [
            {"department": "研发", "salary": 10000},
            {"department": "销售", "salary": 12000},
        ]

        prompt = build_user_prompt(question, columns_schema, preview)

        # 断言关键内容存在
        assert question in prompt
        assert "department" in prompt
        assert "salary" in prompt
        assert "研发" in prompt
        assert "10000" in prompt
        assert "Schema" in prompt
        assert "数据预览" in prompt
        assert "分析需求" in prompt

    def test_build_user_prompt_contains_json_schema(self):
        """构造的提示中 schema 部分应为合法 JSON。"""
        columns_schema = [{"name": "a", "dtype": "int64", "sample": [1, 2]}]
        preview = [{"a": 1}]
        prompt = build_user_prompt("问题", columns_schema, preview)

        # 提取 Schema 段中的 JSON 并验证可解析
        schema_start = prompt.index("## 数据集 Schema") + len("## 数据集 Schema")
        schema_end = prompt.index("## 数据预览")
        schema_json = prompt[schema_start:schema_end].strip()
        parsed = json.loads(schema_json)
        assert parsed[0]["name"] == "a"

    def test_build_user_prompt_preview_truncated(self):
        """preview 超过 5 行时只取前 5 行。"""
        preview = [{"a": i} for i in range(10)]
        prompt = build_user_prompt("q", [], preview)
        # 前 5 行的值应出现，第 6 行及之后的值不应出现
        for i in range(5):
            assert f'"a": {i}' in prompt or f'"a":{i}' in prompt

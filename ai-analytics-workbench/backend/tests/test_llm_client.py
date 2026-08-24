"""LLM 客户端测试：parse_json_response 安全解析（P0 新增）。

不测试 chat_completion（需要真实 API key，由 @retry + 网络），
只测试纯函数 parse_json_response。
"""

import json

import pytest

from app.llm import parse_json_response


class TestParseJsonResponse:
    def test_valid_json(self):
        content = '{"code": "x = 1", "chart_type": "bar"}'
        result = parse_json_response(content)
        assert result["code"] == "x = 1"
        assert result["chart_type"] == "bar"

    def test_json_with_whitespace(self):
        content = '  \n  {"a": 1}  \n  '
        result = parse_json_response(content)
        assert result["a"] == 1

    def test_json_with_prose_before(self):
        content = 'Here is the result:\n{"code": "x = 1"}'
        result = parse_json_response(content)
        assert result["code"] == "x = 1"

    def test_json_with_prose_after(self):
        content = '{"code": "x = 1"}\n以上是分析代码。'
        result = parse_json_response(content)
        assert result["code"] == "x = 1"

    def test_json_surrounded_by_prose(self):
        content = 'Answer:\n{"code": "x = 1"}\n解释：这段代码计算结果。'
        result = parse_json_response(content)
        assert result["code"] == "x = 1"

    def test_nested_json_object(self):
        content = '{"chart_config": {"title": "销售", "series": [{"name": "A", "data": [1, 2]}]}}'
        result = parse_json_response(content)
        assert result["chart_config"]["title"] == "销售"
        assert result["chart_config"]["series"][0]["data"] == [1, 2]

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_response("not json at all")

    def test_empty_object_extracted(self):
        content = "noise {} noise"
        result = parse_json_response(content)
        assert result == {}

    def test_chinese_in_json(self):
        content = '{"summary": "这是一个中文说明"}'
        result = parse_json_response(content)
        assert result["summary"] == "这是一个中文说明"

    def test_code_block_wrapped(self):
        content = '```json\n{"code": "x = 1"}\n```'
        result = parse_json_response(content)
        assert result["code"] == "x = 1"

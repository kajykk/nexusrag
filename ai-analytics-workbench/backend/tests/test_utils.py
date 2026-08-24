"""utils 模块测试：safe_execute_pandas 安全用例 + JSON 序列化（P0 新增）。

重点：覆盖沙箱反射逃逸、IO 禁用、危险 builtins 屏蔽等安全用例。
"""

import json

import numpy as np
import pandas as pd
import pytest

from app.utils import (
    _to_jsonable,
    infer_dataframe_schema,
    safe_execute_pandas,
)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
            "score": [85.5, 92.3, 78.1],
        }
    )


class TestInferDataframeSchema:
    def test_basic_columns(self, sample_df):
        schema = infer_dataframe_schema(sample_df)
        assert len(schema) == 3
        names = [c["name"] for c in schema]
        assert "name" in names
        assert "age" in names
        assert "score" in names

    def test_dtype_inference(self, sample_df):
        schema = infer_dataframe_schema(sample_df)
        dtype_map = {c["name"]: c["dtype"] for c in schema}
        assert "int" in dtype_map["age"].lower() or "Int" in dtype_map["age"]
        assert "float" in dtype_map["score"].lower() or "Float" in dtype_map["score"]

    def test_sample_size(self, sample_df):
        schema = infer_dataframe_schema(sample_df, sample_size=2)
        for c in schema:
            assert len(c["sample"]) == 2

    def test_null_count(self):
        df = pd.DataFrame({"a": [1, None, 3], "b": [None, None, None]})
        schema = infer_dataframe_schema(df)
        null_map = {c["name"]: c["null_count"] for c in schema}
        assert null_map["a"] == 1
        assert null_map["b"] == 3

    def test_unique_count(self):
        df = pd.DataFrame({"a": [1, 1, 2, 3, None]})
        schema = infer_dataframe_schema(df)
        col = next(c for c in schema if c["name"] == "a")
        assert col["unique_count"] == 3  # dropna=True

    def test_jsonable_sample(self, sample_df):
        """sample 字段必须可被 json.dumps 序列化。"""
        schema = infer_dataframe_schema(sample_df)
        for col in schema:
            json.dumps(col["sample"])


class TestSafeExecutePandasBasics:
    def test_simple_assignment(self, sample_df):
        code = "result = df['age'].sum()"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] == ""
        assert out["result"] == 90

    def test_dataframe_result(self, sample_df):
        code = "result = df[['name', 'age']]"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] == ""
        assert isinstance(out["result"], list)
        assert len(out["result"]) == 3
        assert out["result"][0]["name"] == "Alice"

    def test_dict_result(self, sample_df):
        code = "result = {'mean_age': df['age'].mean()}"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] == ""
        assert out["result"]["mean_age"] == 30.0

    def test_no_result_returns_none(self, sample_df):
        code = "x = 1"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] == ""
        assert out["result"] is None

    def test_syntax_error(self, sample_df):
        code = "result = "
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""
        assert "SyntaxError" in out["error"]


class TestSafeExecutePandasSecurity:
    """沙箱安全测试：验证危险 API 被屏蔽。"""

    def test_no_open_builtin(self, sample_df):
        """禁止文件 IO。"""
        code = "result = open('/etc/passwd').read()"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""
        assert "open" in out["error"].lower() or "NameError" in out["error"]

    def test_no_exec_builtin(self, sample_df):
        """禁止 exec/eval 直接调用。"""
        code = "result = eval('1+1')"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""

    def test_no_import(self, sample_df):
        """禁止 __import__。"""
        code = "import os; result = os.listdir('/')"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""

    def test_no_dunder_import(self, sample_df):
        """禁止通过 __import__ 导入危险模块。"""
        code = "result = __import__('os').listdir('/')"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""

    def test_no_subprocess(self, sample_df):
        """禁止 subprocess。"""
        code = "import subprocess; result = subprocess.check_output(['ls']).decode()"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""

    def test_no_subprocess_popen(self, sample_df):
        """禁止 subprocess.Popen（更直接的进程创建 API）。"""
        code = "import subprocess; result = subprocess.Popen(['echo', 'pwned'])"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""

    def test_no_os_system(self, sample_df):
        """禁止 os.system。"""
        code = "import os; result = os.system('echo pwned')"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""

    def test_no_eval_with_builtins_recovery(self, sample_df):
        """禁止通过 __builtins__ 恢复 eval。"""
        code = "result = type('', (), {'__getitem__': lambda self, x: eval(x)})()['1+1']"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""

    def test_no_exit_quit(self, sample_df):
        """禁止 exit/quit。"""
        code = "result = exit()"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""

    def test_pandas_and_numpy_available(self, sample_df):
        """pandas/numpy 必须可用。"""
        code = "result = int(pd is not None) + int(np is not None)"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] == ""
        assert out["result"] == 2

    def test_df_available(self, sample_df):
        """df 变量必须被注入。"""
        code = "result = len(df)"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] == ""
        assert out["result"] == 3

    def test_getattr_blocked_or_limited(self, sample_df):
        """getattr 已从沙箱白名单移除，禁止反射逃逸。

        本用例验证通过 getattr 链不能访问危险对象（如 __class__.__bases__）。
        """
        code = "result = getattr(getattr(df, '__class__'), '__bases__')"
        out = safe_execute_pandas(code, sample_df)
        # 期望：getattr 未定义，抛 NameError
        assert out["error"] != ""
        assert "getattr" in out["error"].lower() or "NameError" in out["error"]

    def test_hasattr_blocked(self, sample_df):
        """hasattr 已从沙箱白名单移除。"""
        code = "result = hasattr(df, 'columns')"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""
        assert "hasattr" in out["error"].lower() or "NameError" in out["error"]

    def test_dunder_class_access_blocked(self, sample_df):
        """禁止直接 dunder 属性访问（如 df.__class__），防止反射逃逸。"""
        code = "result = df.__class__"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""
        assert "受限属性" in out["error"] or "NameError" in out["error"]

    def test_dunder_subclasses_escape_blocked(self, sample_df):
        """禁止经典的 __class__.__bases__[0].__subclasses__() 沙箱逃逸。"""
        code = "result = df.__class__.__bases__[0].__subclasses__()"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""
        assert "受限属性" in out["error"] or "NameError" in out["error"]

    def test_dunder_globals_access_blocked(self, sample_df):
        """禁止 __globals__ 访问。"""
        code = "result = (lambda: None).__globals__"
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] != ""
        assert "受限属性" in out["error"] or "NameError" in out["error"]


class TestToJsonable:
    def test_none(self):
        assert _to_jsonable(None) is None

    def test_dataframe(self):
        df = pd.DataFrame({"a": [1, 2]})
        result = _to_jsonable(df)
        assert isinstance(result, list)
        assert result == [{"a": 1}, {"a": 2}]

    def test_series(self):
        s = pd.Series([1, 2, 3], name="x")
        result = _to_jsonable(s)
        assert result == [1, 2, 3]

    def test_numpy_integer(self):
        assert _to_jsonable(np.int64(42)) == 42
        assert isinstance(_to_jsonable(np.int64(42)), int)

    def test_numpy_float(self):
        result = _to_jsonable(np.float64(3.14))
        assert abs(result - 3.14) < 1e-9
        assert isinstance(result, float)

    def test_numpy_array(self):
        result = _to_jsonable(np.array([1, 2, 3]))
        assert result == [1, 2, 3]

    def test_dict_with_numpy(self):
        result = _to_jsonable({"a": np.int64(1), "b": [np.float64(2.0)]})
        assert result == {"a": 1, "b": [2.0]}

    def test_list_with_mixed(self):
        result = _to_jsonable([1, "x", None, True])
        assert result == [1, "x", None, True]

    def test_pandas_timestamp(self):
        ts = pd.Timestamp("2026-01-01")
        result = _to_jsonable(ts)
        assert isinstance(result, str)
        assert "2026-01-01" in result

    def test_recursive_structure(self):
        result = _to_jsonable({"a": [1, {"b": 2}]})
        assert result == {"a": [1, {"b": 2}]}

    def test_json_serializable_output(self, sample_df):
        """最终输出必须可被 json.dumps 序列化。"""
        result = _to_jsonable(sample_df)
        json.dumps(result)  # 不抛异常即通过

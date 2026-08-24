"""子进程隔离沙箱测试（P1 新增）。

覆盖：正常分析往返、pandas 黑名单读取器拒绝、死循环超时击杀（SANDBOX_TIMEOUT）、
运行异常返回 stderr 摘要、图表 PNG 路径迁出临时目录。

注意：每个用例都会真实拉起 ``python -I`` 子进程（含 pandas 导入开销），
单用例耗时约 2-8 秒，属预期。
"""

import pandas as pd
import pytest

from app.utils.sandbox import ERROR_TIMEOUT, safe_execute_pandas


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
            "score": [85.5, 92.3, 78.1],
        }
    )


class TestSubprocessSandbox:
    def test_normal_analysis_roundtrip(self, sample_df):
        """正常分析：df 经临时目录 CSV 注入子进程，结果以 JSON 形态回传。"""
        code = """
loaded = pd.read_csv('input.csv')
assert list(loaded.columns) == ['name', 'age', 'score']
result = {'rows': int(len(loaded)), 'max_score': float(loaded['score'].max()), 'names': sorted(loaded['name'])}
"""
        out = safe_execute_pandas(code, sample_df)
        assert out["error"] == "", out["error"]
        assert out["error_type"] == ""
        assert out["result"] == {
            "rows": 3,
            "max_score": 92.3,
            "names": ["Alice", "Bob", "Charlie"],
        }

    def test_read_pickle_blacklist_rejected(self, sample_df):
        """黑名单：pd.read_pickle 反序列化入口被直接禁用。"""
        out = safe_execute_pandas("result = pd.read_pickle('evil.pkl')", sample_df)
        assert out["error"] != ""
        assert "read_pickle" in out["error"]
        assert out["result"] is None

    def test_infinite_loop_killed_by_timeout(self, sample_df):
        """死循环：墙钟超时击杀整棵进程树并返回 SANDBOX_TIMEOUT。"""
        out = safe_execute_pandas("while True:\n    x = 1\nresult = 1", sample_df, timeout_seconds=4)
        assert out["error_type"] == ERROR_TIMEOUT
        assert out["error"].startswith(ERROR_TIMEOUT)
        assert out["result"] is None

    def test_runtime_error_returns_stderr_summary(self, sample_df):
        """异常代码：错误消息含异常类型与 stderr 摘要（traceback 尾部）。"""
        out = safe_execute_pandas("result = df['not_a_column']", sample_df)
        assert "KeyError" in out["error"]
        assert "stderr 摘要" in out["error"]
        assert "Traceback" in out["stderr_summary"]

    def test_chart_png_path_moved_to_artifacts_dir(self, sample_df, tmp_path):
        """图表 PNG 路径：子进程透传的文件被迁出临时目录到持久目录。"""
        code = "result = {'ok': True}\nchart_png_path = 'input.csv'"
        out = safe_execute_pandas(code, sample_df, artifacts_dir=str(tmp_path))
        assert out["error"] == "", out["error"]
        persisted = out["chart_png_path"]
        assert persisted is not None
        assert str(tmp_path) in persisted
        assert persisted.endswith(".png")

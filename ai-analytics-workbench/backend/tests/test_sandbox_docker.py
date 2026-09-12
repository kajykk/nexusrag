"""容器级隔离沙箱测试（SANDBOX_MODE=docker）。

覆盖（docker 引擎可用时跑真容器；不可用则整体 skip，不阻塞 CI）：
- 正常分析往返：df 经挂载目录 CSV 注入容器，结果文件协议与子进程模式一致；
- read_pickle 黑名单仍前置拦截（容器内守卫与子进程模式同源生效）；
- 死循环超时：墙钟超时触发 docker kill 击杀容器，返回 SANDBOX_TIMEOUT；
- 容器命令行静态断言：--network=none 网络硬隔离与 cgroups 资源上限在场。

注意：真容器用例单条耗时约 3-15 秒（含容器启动与 pandas 导入），属预期；
首次运行会把 pandas/numpy 装进持久依赖卷（约 1-2 分钟，仅一次）。
"""

import os
import time
from pathlib import Path

import pandas as pd
import pytest

from app.config import settings
from app.utils.sandbox import (
    ERROR_TIMEOUT,
    _build_docker_command,
    _docker_cli_available,
    safe_execute_pandas,
)


@pytest.fixture(scope="module")
def docker_sandbox():
    """docker 引擎可用时把 SANDBOX_MODE 切到 docker；不可用则跳过本模块。"""
    if not _docker_cli_available():
        pytest.skip("Docker 引擎不可用，跳过容器级沙箱测试")
    mp = pytest.MonkeyPatch()
    mp.setattr(settings, "SANDBOX_MODE", "docker")
    yield
    mp.undo()


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35],
            "score": [85.5, 92.3, 78.1],
        }
    )


class TestDockerSandbox:
    def test_normal_analysis_roundtrip_in_container(self, docker_sandbox, sample_df):
        """正常分析：临时目录挂载进出容器，结果以 JSON 形态回传。"""
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

    def test_read_pickle_blacklist_rejected_in_container(self, docker_sandbox, sample_df):
        """黑名单前置：pd.read_pickle 反序列化入口在容器内同样被直接禁用。"""
        out = safe_execute_pandas("result = pd.read_pickle('evil.pkl')", sample_df)
        assert out["error"] != ""
        assert "read_pickle" in out["error"]
        assert out["result"] is None

    def test_runtime_error_returns_stderr_summary_in_container(self, docker_sandbox, sample_df):
        """异常代码：错误消息含异常类型与 stderr 摘要（traceback 尾部）。"""
        out = safe_execute_pandas("result = df['not_a_column']", sample_df)
        assert "KeyError" in out["error"]
        assert "stderr 摘要" in out["error"]
        assert "Traceback" in out["stderr_summary"]

    def test_infinite_loop_killed_by_docker_kill(self, docker_sandbox, sample_df):
        """死循环：墙钟超时触发 docker kill，返回 SANDBOX_TIMEOUT 且击杀及时。"""
        started = time.monotonic()
        out = safe_execute_pandas("while True:\n    x = 1\nresult = 1", sample_df, timeout_seconds=6)
        elapsed = time.monotonic() - started
        assert out["error_type"] == ERROR_TIMEOUT
        assert out["error"].startswith(ERROR_TIMEOUT)
        assert "容器" in out["error"]
        assert out["result"] is None
        # 击杀及时：远小于默认 30s 时限级别，证明 docker kill 生效而非悬挂
        assert elapsed < 60


class TestDockerCommandShape:
    def test_command_has_hard_isolation_flags(self, tmp_path):
        """容器命令静态断言：网络硬隔离、cgroups 上限、HOME 与入口必须在场。"""
        cmd = _build_docker_command(tmp_path, "aiwb_sandbox_test", None)
        assert "--network=none" in cmd
        idx = {flag: cmd.index(flag) for flag in ("--memory", "--cpus", "--pids-limit")}
        assert cmd[idx["--memory"] + 1] == "512m"
        assert cmd[idx["--cpus"] + 1] == "1"
        assert cmd[idx["--pids-limit"] + 1] == "128"
        assert "HOME=/tmp" in cmd
        # 卷挂载：宿主临时目录 -> /work（Windows 下为正斜杠盘符路径）
        mount = next(arg for arg in cmd if arg.endswith(":/work"))
        host_part = mount[: -len(":/work")]
        assert Path(host_part).is_absolute()
        assert host_part.replace("\\", "/") == os.path.abspath(tmp_path).replace("\\", "/")
        # 入口：包装脚本随工作目录挂入，保证结果协议与黑名单和子进程模式一致
        # （容器内路径为 POSIX 风格，不受宿主平台影响）
        assert cmd[-2:] == ["python", "/work/sandbox_child.py"]

    def test_command_mounts_deps_volume_readonly_when_provided(self, tmp_path):
        """镜像缺 pandas 时应只读挂载依赖卷并注入 PYTHONPATH。"""
        cmd = _build_docker_command(tmp_path, "aiwb_sandbox_test", "aiwb_sandbox_deps_x")
        assert "aiwb_sandbox_deps_x:/opt/pydeps:ro" in cmd
        assert "PYTHONPATH=/opt/pydeps" in cmd

"""沙箱子进程包装脚本（由 app/utils/sandbox.py 以 ``sys.executable -I <本文件>`` 启动）。

自包含设计：``-I`` 隔离模式下 sys.path 既不含脚本所在目录也不含用户路径，
因此本脚本禁止 import app.*；全部配置经工作目录下的 ``config.json`` 注入
（名单的单一事实来源维护在 sandbox.py，避免双份漂移）。

约定文件（cwd = 主进程创建的一次性临时工作目录）：
  输入:
    - ``input.csv``    主进程落盘的输入 DataFrame
    - ``user_code.py`` 待执行的用户分析代码
    - ``config.json``  白名单/黑名单/资源限制等配置
  输出:
    - ``result.json``          必写：状态 + JSON 化结果
    - ``result.csv``           结果为 DataFrame 时另存全量 CSV
    - ``<用户自定义>.png``      用户代码设置全局变量 ``chart_png_path`` 时透传其路径

执行流程：POSIX 资源限制(尽力而为) -> 重建受限 builtins 与 pandas IO 守卫 ->
AST 复核 -> exec 用户代码 -> 序列化结果 -> 写 result.json -> exit 0。

异常协议：用户代码抛出的任何异常都被捕获，以 result.json(status=error) 上报，
同时打印 traceback 到 stderr（供主进程生成 stderr 摘要）；硬崩溃（OOM/SIGKILL
等）不会留下 result.json，由主进程按"异常退出"兜底处理。
"""

import ast
import builtins
import datetime
import json
import math
import os
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd


def _apply_posix_rlimits(cpu_seconds: int, max_memory_bytes: int) -> None:
    """POSIX 资源限制：RLIMIT_CPU / RLIMIT_AS，尽力而为。

    Windows 无 setrlimit（更无 seccomp），直接跳过——该平台的资源约束
    由主进程的墙钟超时击杀兜底；POSIX 上个别内核/容器也可能不支持
    特定 limit，失败时降级为不限制，不阻断分析执行。
    """
    if os.name != "posix":
        return
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
    except Exception:
        print("[sandbox] POSIX 资源限制施加失败，降级为不限制", file=sys.stderr)


def _reject_dunder_attributes(source: str) -> None:
    """AST 复核：禁止所有 ``_`` 开头的属性访问（与主进程同一道门的纵深防御）。"""
    tree = ast.parse(source, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise NameError(f"禁止访问受限属性: {node.attr}")


def _build_restricted_builtins(allowed_names: list[str]) -> dict:
    """按白名单重建受限 builtins；True/False/None 是编译器字面量，天然可用。"""
    real = vars(builtins)
    return {name: real[name] for name in allowed_names if name in real}


def _make_blocked_reader(name: str):
    def _blocked(*args, **kwargs):  # noqa: ANN002, ANN003
        raise PermissionError(f"沙箱已禁用 pd.{name}（反序列化/外部格式入口可能执行任意代码）")

    _blocked.__name__ = f"{name}_blocked"
    return _blocked


def _contains_url(args: tuple, kwargs: dict) -> bool:
    def _check(value) -> bool:
        return isinstance(value, str) and "://" in value

    for arg in (*args, *kwargs.values()):
        if _check(arg):
            return True
        if isinstance(arg, list | tuple | set) and any(_check(item) for item in arg):
            return True
    return False


def _make_url_guarded_reader(name: str, func):
    def _guarded(*args, **kwargs):  # noqa: ANN002, ANN003
        if _contains_url(args, kwargs):
            raise PermissionError(f"沙箱禁止通过 pd.{name} 访问网络资源（URL 参数）")
        return func(*args, **kwargs)

    _guarded.__name__ = f"{name}_url_guarded"
    return _guarded


def _install_pd_guards(blocked_readers: list[str], url_guarded_readers: list[str]) -> None:
    """直接替换 pandas 模块上的危险 IO 入口。

    说明：子进程是一次性（throwaway）进程，原地修改 pd 无需构造模块代理。
    """
    for name in blocked_readers:
        if hasattr(pd, name):
            setattr(pd, name, _make_blocked_reader(name))
    for name in url_guarded_readers:
        func = getattr(pd, name, None)
        if callable(func):
            setattr(pd, name, _make_url_guarded_reader(name, func))


def _jsonable(obj, state: dict):
    """递归转 JSON 可序列化结构；DataFrame 首次出现时另存全量 CSV。

    records 明细最多序列化 ``state["max_record_rows"]`` 行，防止超大结果
    在进程间搬运撑爆内存/管道（CSV 侧仍保留全量数据供持久化使用）。
    """
    if obj is None:
        return None
    if isinstance(obj, pd.DataFrame):
        if not state["csv_written"]:
            obj.to_csv(state["csv_path"], index=False)
            state["csv_written"] = True
        head = obj.head(state["max_record_rows"])
        return json.loads(head.to_json(orient="records", force_ascii=False, date_format="iso"))
    if isinstance(obj, pd.Series):
        return json.loads(
            obj.head(state["max_record_rows"]).to_json(orient="records", force_ascii=False, date_format="iso")
        )
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        value = float(obj)
        return value if math.isfinite(value) else None
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, datetime.datetime | datetime.date | datetime.time):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(key): _jsonable(value, state) for key, value in obj.items()}
    if isinstance(obj, list | tuple | set):
        return [_jsonable(item, state) for item in obj]
    return obj


def main() -> int:
    cfg = json.loads(Path("config.json").read_text(encoding="utf-8"))
    _apply_posix_rlimits(int(cfg["cpu_seconds"]), int(cfg["max_memory_bytes"]))

    source = Path("user_code.py").read_text(encoding="utf-8")

    # 输入数据来自主进程复制的受信 CSV（本地路径，非 URL，不会被守卫拦截）
    df = pd.read_csv("input.csv")

    # 纵深防御：主进程已做过同一 AST 校验，这里复核一次
    _reject_dunder_attributes(source)

    sandbox_globals = {
        "__builtins__": _build_restricted_builtins(cfg["allowed_builtins"]),
        "pd": pd,
        "np": np,
        "df": df,
    }
    _install_pd_guards(cfg["blocked_readers"], cfg["url_guarded_readers"])

    state = {
        "csv_written": False,
        "csv_path": "result.csv",
        "max_record_rows": int(cfg["max_record_rows"]),
    }

    try:
        exec(compile(source, "user_code.py", "exec"), sandbox_globals)  # noqa: S102
        chart_png_path = sandbox_globals.get("chart_png_path") or sandbox_globals.get("chart_path")
        payload = {
            "status": "ok",
            "result": _jsonable(sandbox_globals.get("result"), state),
            "result_csv": state["csv_path"] if state["csv_written"] else None,
            "chart_png_path": chart_png_path if isinstance(chart_png_path, str) and chart_png_path else None,
        }
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()  # 进入 stderr，主进程生成摘要
        payload = {"status": "error", "error_type": type(exc).__name__, "error": str(exc)}

    Path("result.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

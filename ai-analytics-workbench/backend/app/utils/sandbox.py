"""受限沙箱：在受限命名空间内执行 Pandas 代码。

安全要点：
1. AST 级校验（``_validate_sandbox_code``）拦截所有 ``_`` 开头的属性访问，
   防止 ``df.__class__.__bases__`` 等反射逃逸。
2. ``__builtins__`` 白名单仅暴露数据处理的纯函数，移除 ``getattr`` / ``hasattr`` /
   ``delattr`` / ``eval`` / ``exec`` / ``open`` 等。
3. 仅注入 ``pd`` / ``np`` / ``df`` 三个全局对象。
4. pandas 危险 IO 入口黑名单：``read_pickle`` / ``read_stata`` 直接禁用
   （反序列化可执行任意代码、stata 文件解析历史漏洞多）；
   ``read_csv`` / ``read_json`` / ``read_html`` / ``read_excel`` /
   ``read_table`` / ``read_fwf`` 等读取函数被包装，任一字符串参数含
   ``://``（即 http/https/ftp 等 URL）时拒绝执行，阻断网络入口。

⚠️ 当前防护边界（如实说明，本沙箱并非硬隔离）：
- 仅拦截 pandas 顶层读取器的 URL 参数；传入本地文件路径的读取调用
  （如 ``pd.read_csv("local.csv")``）目前不会被拦截——依赖 builtins 中无
  ``open`` 以及 AST 校验间接防护，属于已知薄弱点。
- ``numpy.load(allow_pickle=True)``、h5py、scipy.io 等其他库的反序列化
  入口未逐一封堵。
- 本方案是同进程内的"受限命名空间"，不是操作系统级沙箱；生产环境建议
  叠加容器隔离（独立用户/网络命名空间/seccomp）或改用进程外执行。
"""

import ast

import pandas as pd

from app.utils.schema import _to_jsonable

# 直接禁用的反序列化/外部格式入口
_BLOCKED_READERS = (
    "read_pickle",
    "read_stata",
)

# 参数中出现 "://" 即拒绝的网络相关读取入口
_URL_GUARDED_READERS = (
    "read_csv",
    "read_json",
    "read_html",
    "read_excel",
    "read_table",
    "read_fwf",
    "read_sas",
    "read_spss",
)


def _validate_sandbox_code(code: str) -> None:
    """AST 级校验：禁止 dunder 属性访问，防止反射逃逸。

    背景：仅限制 __builtins__ 无法阻止直接属性访问如
    ``df.__class__.__bases__[0].__subclasses__()``，此类链式访问
    可获取 subprocess 等危险对象。本函数在 exec 前拦截所有以 ``_``
    开头的属性访问。
    """
    tree = ast.parse(code, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise NameError(f"禁止访问受限属性: {node.attr}")


def _make_blocked_reader(name: str):
    """生成直接禁用读取器的替代实现。"""

    def _blocked(*args, **kwargs):  # noqa: ANN002, ANN003
        raise PermissionError(
            f"沙箱已禁用 pd.{name}（反序列化/外部格式入口可能执行任意代码）"
        )

    _blocked.__name__ = f"{name}_blocked"
    return _blocked


def _contains_url(args: tuple, kwargs: dict) -> bool:
    """检查位置/关键字参数中是否有字符串包含 '://'（网络 URL 特征）。"""

    def _check(value) -> bool:
        return isinstance(value, str) and "://" in value

    for arg in args:
        if _check(arg):
            return True
        if isinstance(arg, (list, tuple, set)):  # noqa: UP038
            if any(_check(item) for item in arg):
                return True
    for value in kwargs.values():
        if _check(value):
            return True
        if isinstance(value, (list, tuple, set)):  # noqa: UP038
            if any(_check(item) for item in value):
                return True
    return False


def _make_url_guarded_reader(name: str, func):
    """包装读取器：任一字符串参数含 '://' 时拒绝执行。"""

    def _guarded(*args, **kwargs):  # noqa: ANN002, ANN003
        if _contains_url(args, kwargs):
            raise PermissionError(f"沙箱禁止通过 pd.{name} 访问网络资源（URL 参数）")
        return func(*args, **kwargs)

    _guarded.__name__ = f"{name}_url_guarded"
    return _guarded


def _build_pandas_proxy() -> pd:
    """返回替换了危险 IO 入口的 pandas 模块代理。"""
    replacements: dict = {}
    for name in _BLOCKED_READERS:
        if hasattr(pd, name):
            replacements[name] = _make_blocked_reader(name)
    for name in _URL_GUARDED_READERS:
        func = getattr(pd, name, None)
        if callable(func):
            replacements[name] = _make_url_guarded_reader(name, func)
    if not replacements:
        return pd
    # type(...) 动态创建 pd 的浅拷贝代理，仅替换指定属性
    proxy = type("SandboxPandasProxy", (), {k: getattr(pd, k) for k in dir(pd) if not k.startswith("_")})
    for name, replacement in replacements.items():
        setattr(proxy, name, replacement)
    return proxy


def safe_execute_pandas(code: str, df: pd.DataFrame) -> dict:
    """在受限沙箱中执行 Pandas 代码。

    只暴露 pandas / numpy / 标准库白名单子集，禁用反序列化与网络读取入口
    （防护边界见模块 docstring）。
    返回 {"result": ..., "error": ""}
    """
    import numpy as np

    sandbox_globals = {
        "__builtins__": {
            name: __builtins__[name] if isinstance(__builtins__, dict) else getattr(__builtins__, name)
            for name in (
                "abs",
                "all",
                "any",
                "bool",
                "dict",
                "enumerate",
                "filter",
                "float",
                "int",
                "len",
                "list",
                "map",
                "max",
                "min",
                "print",
                "range",
                "round",
                "set",
                "slice",
                "sorted",
                "str",
                "sum",
                "tuple",
                "type",
                "zip",
                "True",
                "False",
                "None",
                "isinstance",
                "issubclass",
                "sorted",
                "reversed",
                "format",
                "repr",
                # 安全说明：getattr / hasattr / delattr 已从白名单移除，避免反射逃逸
                # （如 getattr(df, '__class__').__bases__ 链式访问危险对象）
            )
        },
        "pd": _build_pandas_proxy(),
        "np": np,
        "df": df,
    }
    try:
        _validate_sandbox_code(code)
        exec(code, sandbox_globals)  # noqa: S102
        result = sandbox_globals.get("result", None)
        return {"result": _to_jsonable(result), "error": ""}
    except Exception as exc:  # noqa: BLE001
        return {"result": None, "error": f"{type(exc).__name__}: {exc}"}

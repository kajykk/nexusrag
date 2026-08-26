"""沙箱：在隔离环境中执行 Pandas 分析代码，支持两种可选隔离模式。

模式选择（SANDBOX_MODE，默认 subprocess）：

- **subprocess**（默认）：一次性子进程 + ``python -I`` 隔离模式执行。
- **docker**：一次性容器执行（``SANDBOX_DOCKER_IMAGE`` 配置镜像，
  默认 python:3.12-alpine；本地缺失时自动 ``docker pull``，pull 失败
  回退 subprocess 并记录 warning）。容器以
  ``--network=none --memory=512m --cpus=1 --pids-limit=128`` 启动，
  临时工作目录挂载为 /work，超时后 ``docker kill`` 击杀。
  docker CLI 不可用时同样自动回退 subprocess 并 warning。

两种模式共享同一套防护与结果文件协议（result.json / result.csv /
chart_png_path），AST 门、pandas IO 黑名单、受限 builtins 白名单全部一致：
容器模式把包装脚本 sandbox_child.py 一并复制进临时目录，以
``python /work/sandbox_child.py`` 作为容器入口（其内部再 exec 用户代码），
因此 read_pickle 等黑名单在容器内同样生效。

威胁模型对照表（如实说明）：

| 防线 | subprocess 模式 | docker 模式 |
|------|----------------|-------------|
| 反射逃逸（dunder 属性链） | AST 门 + 子进程 AST 复核 | 同左 |
| pandas 反序列化/URL 入口 | 子进程内守卫替换 pd.* | 同左（容器内生效） |
| 受限 builtins 白名单 | exec 前重建 | 同左 |
| CPU/内存限制 | POSIX rlimit 尽力而为；Windows 仅墙钟超时兜底 | cgroups 硬限（--memory/--cpus/--pids-limit），全平台一致 |
| 网络 | **无硬隔离**：子进程持有真实 socket 栈，仅剥离代理变量 + URL 参数守卫收窄面 | **硬隔离**：--network=none，容器无网络栈路由 |
| 文件系统 | 共享宿主文件系统权限 | 仅 /work 临时目录挂载进出 |
| 超时 | taskkill /F /T 或 killpg 整树击杀 | docker kill 击杀容器 |

docker 模式已知边界（如实说明）：Docker daemon 自身的攻击面（socket 权限、
镜像供应链）不在本沙箱防护范围内；Windows 上依赖 Docker Desktop 的
卷挂载路径转换（win 路径正斜杠形式实测可用）；默认 alpine 镜像不带
pandas/numpy，首次运行会把依赖 pip 安装进持久命名卷只读挂载（见
``_ensure_pandas_deps_volume``），自定义镜像自带 pandas 时自动跳过。

架构（静态门 + 隔离执行 + 运行时围栏）：

第一道 —— 静态 AST 门（主进程，启动子进程前零成本拒绝）
1. ``_validate_sandbox_code`` 拦截所有 ``_`` 开头的属性访问，防止
   ``df.__class__.__bases__[0].__subclasses__()`` 等反射逃逸；
2. pandas 危险 IO 入口黑名单：``read_pickle`` / ``read_stata`` 直接禁用
   （反序列化可执行任意代码、解析器历史漏洞多）；``read_csv`` /
   ``read_json`` / ``read_html`` / ``read_excel`` 等读取函数被包装，
   任一字符串参数含 ``://``（http/https/ftp 等 URL）时拒绝执行。

第二道 —— 隔离执行（subprocess 子进程 / docker 容器，二选一）
1. 主进程创建一次性临时工作目录：输入 DataFrame 落盘为 ``input.csv``，
   用户代码写为 ``user_code.py``，白名单/资源配置写为 ``config.json``；
2. 以 ``sys.executable -I``（隔离模式：忽略环境变量与 PYTHONPATH、不加载
   用户 site-packages、cwd 不进 sys.path）+ 受限环境变量白名单启动子进程
   运行自包含包装脚本 ``sandbox_child.py``；
3. 包装脚本内重建受限 builtins 白名单后 exec 用户代码，把结果序列化到约定
   文件（``result.json``；DataFrame 另存 ``result.csv``；用户代码设置的
   ``chart_png_path`` 全局变量作为图表 PNG 路径透传）；
4. 主进程带超时等待（默认 30s，可用环境变量 ``SANDBOX_TIMEOUT_SECONDS``
   或参数 ``timeout_seconds`` 配置），超时击杀整个进程树——Windows 用
   ``taskkill /F /T``，POSIX 对独立进程组发 SIGKILL；
5. 无论成败，临时目录最终一律删除，不留残留文件。

平台差异（如实说明）：
- Windows 无 setrlimit/seccomp。当前在 Windows 上的防线 =
  AST 静态门 + 子进程隔离 + 墙钟超时击杀 + 临时目录清理 + 环境变量剥离；
  CPU/内存约束由超时机制兜底。
- POSIX 分支在包装脚本内 try/except 施加 RLIMIT_CPU / RLIMIT_AS
  （尽力而为，限制失败降级为不限制，不阻断执行）。

网络边界（如实说明，仅 subprocess 模式）：本沙箱对网络**不做硬承诺**——
子进程持有真实 socket 栈，理论上仍可发起直连（需要网络硬隔离时请切换
docker 模式，``--network=none`` 由网络命名空间保证容器无路由）；
但 subprocess 模式已剥离 HTTP_PROXY / HTTPS_PROXY / ALL_PROXY / NO_PROXY
等代理类环境变量，仅保留最小环境集合，pandas 读取器的 URL 参数亦被守卫拦截。

已封堵的反序列化入口：pandas 顶层读取器（黑名单/URL 守卫）；
``np.load`` 在子进程内被强制包装——默认拒绝 pickle，显式
``allow_pickle=True`` 直接抛 PermissionError（pickle reduce 可执行
任意构造器，绕过 AST 属性门）。h5py、scipy.io 未在白名单内，
用户代码无法 import（受限 builtins 无 __import__）。
"""

import ast
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# 超时错误类型标识：safe_execute_pandas 返回值 error_type 字段使用
ERROR_OK = ""
ERROR_TIMEOUT = "SANDBOX_TIMEOUT"
ERROR_EXECUTION = "SANDBOX_ERROR"


class SandboxTimeoutError(RuntimeError):
    """沙箱执行体（子进程树 / 容器）超过墙钟时限被强制终止。

    公共接口 ``safe_execute_pandas`` 将其转换为 ``error_type=SANDBOX_TIMEOUT``
    的返回值；调用方既可捕获本异常类型（低层 API），也可按常量分支处理。
    subprocess 模式击杀整棵进程树，docker 模式 ``docker kill`` 击杀容器。
    """

    def __init__(self, message: str, stderr_summary: str = "") -> None:
        super().__init__(message)
        self.stderr_summary = stderr_summary


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

# 受限 builtins 白名单（经 config.json 注入子进程重建）。
# 安全说明：getattr / hasattr / delattr / eval / exec / open / __import__ /
# compile / input / memoryview 等反射或 IO 入口一律不在白名单；
# True / False / None 为编译器字面量，无需注入即始终可用。
_ALLOWED_BUILTINS = (
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "filter",
    "float",
    "format",
    "int",
    "isinstance",
    "issubclass",
    "len",
    "list",
    "map",
    "max",
    "min",
    "print",
    "range",
    "repr",
    "reversed",
    "round",
    "set",
    "slice",
    "sorted",
    "str",
    "sum",
    "tuple",
    "type",
    "zip",
)

# 子进程环境变量白名单（大小写不敏感匹配；Windows 必需 SystemRoot）
_ENV_ALLOW_KEYS = (
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "PATH",
    "LANG",
    "LC_ALL",
    "HOME",
)

_CHILD_SCRIPT = Path(__file__).with_name("sandbox_child.py")

# POSIX RLIMIT_AS 默认上限（无独立配置项，如需放宽请改此处并同步评估风险）
_DEFAULT_MAX_MEMORY_BYTES = 512 * 1024 * 1024
# RLIMIT_CPU 在墙钟超时基础上留出的余量下限
_MIN_CPU_SECONDS = 10
# result.json 中 records 明细的最大行数（CSV 侧保留全量）
_MAX_RECORD_ROWS = 1000
_STDERR_SUMMARY_CHARS = 2000

# ── docker 模式常量 ──
_DOCKER_WORKDIR = "/work"
# cgroups 硬资源上限（与 subprocess 模式的 rlimit/超时策略对齐）
_DOCKER_MEMORY = "512m"
_DOCKER_CPUS = "1"
_DOCKER_PIDS_LIMIT = "128"
# 镜像探测 / pull / 依赖安装的墙钟上限
_DOCKER_PROBE_TIMEOUT_SECONDS = 120
_DOCKER_PULL_TIMEOUT_SECONDS = 600
_DEPS_INSTALL_TIMEOUT_SECONDS = 900
# 默认 alpine 镜像无 pandas/numpy：装进持久命名卷只读挂载，避免每次重装
_DEPS_VOLUME_PREFIX = "aiwb_sandbox_deps"
_DEPS_MOUNT_TARGET = "/opt/pydeps"
_DEPS_SENTINEL = ".aiwb_deps_ok"
_DEPS_PACKAGES = "pandas numpy"
# 进程内缓存：镜像探测结果按镜像名记忆，避免每次执行都拉起探测容器
_pandas_probe_cache: dict[str, bool] = {}


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


def _build_child_env() -> dict[str, str]:
    """构造子进程的最小环境集合。

    仅透传白名单键（见 ``_ENV_ALLOW_KEYS``），其余全部剥离——包括
    HTTP_PROXY / HTTPS_PROXY / ALL_PROXY / NO_PROXY 等代理类变量与可能
    含敏感信息的业务密钥。网络不做硬承诺（见模块 docstring），剥离代理
    变量只是收窄面而非硬隔离。
    """
    upper = {key.upper(): value for key, value in os.environ.items()}
    env = {key: upper[key] for key in _ENV_ALLOW_KEYS if key in upper}
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # 双保险：即便白名单日后扩宽，也绝不向子进程泄漏代理类变量
    for key in [key for key in env if "PROXY" in key.upper()]:
        env.pop(key)
    return env


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """超时后击杀整棵进程树，防止用户代码再 fork 出孤儿进程。"""
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(  # noqa: S603
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                check=False,
                capture_output=True,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:  # noqa: BLE001 兜底：至少尝试直接杀主进程
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


def _docker_cli_available() -> bool:
    """docker CLI 存在且 daemon 可达；不可达视为 docker 模式不可用。"""
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(  # noqa: S603
            ["docker", "version", "--format", "{{.Server.Version}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def _ensure_docker_image(image: str) -> bool:
    """确保镜像本地存在：inspect 命中直接用，缺失则 pull；失败返回 False。"""
    try:
        inspect = subprocess.run(  # noqa: S603
            ["docker", "image", "inspect", image],
            check=False,
            capture_output=True,
            timeout=_DOCKER_PROBE_TIMEOUT_SECONDS,
        )
        if inspect.returncode == 0:
            return True
        logger.warning("沙箱镜像 %s 本地不存在，正在 docker pull ...", image)
        pull = subprocess.run(  # noqa: S603
            ["docker", "pull", image],
            check=False,
            capture_output=True,
            text=True,
            timeout=_DOCKER_PULL_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("检查/拉取沙箱镜像 %s 失败：%s，回退 subprocess 模式", image, exc)
        return False
    if pull.returncode != 0:
        logger.warning(
            "docker pull %s 失败：%s，回退 subprocess 模式",
            image,
            (pull.stderr or "").strip()[-_STDERR_SUMMARY_CHARS:],
        )
        return False
    return True


def _image_has_pandas(image: str) -> bool:
    """探测镜像内是否自带 pandas/numpy（自定义镜像常见），结果按镜像缓存。"""
    cached = _pandas_probe_cache.get(image)
    if cached is not None:
        return cached
    try:
        proc = subprocess.run(  # noqa: S603
            [
                "docker",
                "run",
                "--rm",
                "--network=none",
                image,
                "python",
                "-c",
                "import pandas, numpy",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=_DOCKER_PROBE_TIMEOUT_SECONDS,
        )
        ok = proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    _pandas_probe_cache[image] = ok
    return ok


def _ensure_pandas_deps_volume(image: str) -> str | None:
    """默认 alpine 镜像无 pandas：把依赖 pip 安装进持久命名卷供分析容器只读挂载。

    返回依赖卷名；准备失败返回 None（调用方回退 subprocess）。安装容器需要
    网络（PyPI），分析容器仍以 --network=none 启动，二者互不影响。
    """
    volume = f"{_DEPS_VOLUME_PREFIX}_{hashlib.sha256(image.encode()).hexdigest()[:10]}"
    try:
        marker_check = subprocess.run(  # noqa: S603
            ["docker", "run", "--rm", "-v", f"{volume}:/deps", image, "test", "-f", f"/deps/{_DEPS_SENTINEL}"],
            check=False,
            capture_output=True,
            timeout=_DOCKER_PROBE_TIMEOUT_SECONDS,
        )
        if marker_check.returncode == 0:
            return volume
        logger.warning(
            "镜像 %s 缺少 pandas/numpy，首次运行将安装到依赖卷 %s（约 1-2 分钟）...",
            image,
            volume,
        )
        install = subprocess.run(  # noqa: S603
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{volume}:/deps",
                "-w",
                "/deps",
                image,
                "sh",
                "-c",
                (
                    f"pip install --no-cache-dir --target=/deps {_DEPS_PACKAGES}"
                    f" && touch {_DEPS_SENTINEL}"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=_DEPS_INSTALL_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("沙箱依赖卷准备失败：%s，回退 subprocess 模式", exc)
        return None
    if install.returncode != 0:
        logger.warning(
            "依赖卷 pip install 失败：%s，回退 subprocess 模式",
            (install.stderr or "").strip()[-_STDERR_SUMMARY_CHARS:],
        )
        return None
    return volume


def _docker_volume_path(workdir: Path) -> str:
    """宿主临时目录转 docker -v 卷路径。

    Windows 下 os.path.abspath 产生反斜杠盘符路径（E:\\code\\...），Docker
    Desktop 对正斜杠形式 E:/code/... 自动做路径转换，实测可用；POSIX 直接用绝对路径。
    """
    abspath = os.path.abspath(workdir)
    return abspath.replace("\\", "/") if os.name == "nt" else abspath


def _build_docker_command(workdir: Path, container_name: str, deps_volume: str | None) -> list[str]:
    """构造一次性分析容器的完整命令行（--network=none 网络硬隔离是核心增强）。"""
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "--memory",
        _DOCKER_MEMORY,
        "--cpus",
        _DOCKER_CPUS,
        "--pids-limit",
        _DOCKER_PIDS_LIMIT,
        "--name",
        container_name,
        "-v",
        f"{_docker_volume_path(workdir)}:{_DOCKER_WORKDIR}",
        "-w",
        _DOCKER_WORKDIR,
        "-e",
        "HOME=/tmp",
    ]
    if deps_volume:
        cmd += ["-v", f"{deps_volume}:{_DEPS_MOUNT_TARGET}:ro", "-e", f"PYTHONPATH={_DEPS_MOUNT_TARGET}"]
    # 容器内路径必须是 POSIX 风格（Path("/work") 在 Windows 会产生反斜杠）
    child_in_container = _DOCKER_WORKDIR + "/" + _CHILD_SCRIPT.name
    cmd += [settings.SANDBOX_DOCKER_IMAGE, "python", child_in_container]
    return cmd


def _write_workdir(
    workdir: Path,
    *,
    df: pd.DataFrame,
    code: str,
    timeout_seconds: float,
    include_child_script: bool = False,
) -> None:
    """落盘执行环境约定的输入文件：input.csv / user_code.py / config.json。

    docker 模式额外把包装脚本复制进临时目录（容器内只看得到挂载的 /work，
    不能引用宿主包路径），子进程模式仍从安装目录直接启动脚本。
    """
    df.to_csv(workdir / "input.csv", index=False)
    (workdir / "user_code.py").write_text(code, encoding="utf-8")
    if include_child_script:
        shutil.copyfile(_CHILD_SCRIPT, workdir / _CHILD_SCRIPT.name)
    cpu_seconds = max(int(timeout_seconds) + 5, _MIN_CPU_SECONDS)
    config = {
        "allowed_builtins": list(_ALLOWED_BUILTINS),
        "blocked_readers": list(_BLOCKED_READERS),
        "url_guarded_readers": list(_URL_GUARDED_READERS),
        "cpu_seconds": cpu_seconds,
        "max_memory_bytes": _DEFAULT_MAX_MEMORY_BYTES,
        "max_record_rows": _MAX_RECORD_ROWS,
    }
    (workdir / "config.json").write_text(json.dumps(config), encoding="utf-8")


def _run_child(workdir: Path, timeout_seconds: float) -> tuple[dict | None, str, int | None]:
    """以隔离模式运行子进程并等待结束。

    返回 ``(payload, stderr_text, returncode)``；``payload`` 为
    result.json 解析结果（文件缺失或损坏时为 None）。墙钟超时抛出
    :class:`SandboxTimeoutError` 并先击杀整棵进程树。
    """
    popen_kwargs: dict = {
        "cwd": str(workdir),
        "env": _build_child_env(),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        popen_kwargs["start_new_session"] = True  # 独立进程组：便于 killpg 整树击杀

    proc = subprocess.Popen([sys.executable, "-I", str(_CHILD_SCRIPT)], **popen_kwargs)  # noqa: S603
    timed_out = False
    stderr_text = ""
    try:
        _, stderr_text = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_process_tree(proc)
        try:
            _, stderr_text = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stderr_text = ""

    if timed_out:
        summary = _summarize_stderr(stderr_text)
        raise SandboxTimeoutError(f"SANDBOX_TIMEOUT: 执行超过 {timeout_seconds:g}s，子进程树已被强制终止", summary)

    payload: dict | None = None
    result_file = workdir / "result.json"
    if result_file.is_file():
        try:
            payload = json.loads(result_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = None
    return payload, stderr_text or "", proc.returncode


def _resolve_docker_deps_volume(image: str) -> str | None:
    """镜像自带 pandas 则无需依赖卷；否则准备持久依赖卷，失败返回 None。"""
    if _image_has_pandas(image):
        return ""
    return _ensure_pandas_deps_volume(image)


def _run_docker(
    workdir: Path,
    timeout_seconds: float,
    *,
    container_name: str,
    deps_volume: str | None,
) -> tuple[dict | None, str, int | None]:
    """以一次性容器运行沙箱并等待结束（结果文件协议与 _run_child 一致）。

    容器入口为 ``python /work/sandbox_child.py``（包装脚本随临时目录挂入），
    由其 exec 用户代码并写 result.json。墙钟超时先 ``docker kill`` 击杀
    容器（--rm 随后自动清理），再收割 docker CLI 进程。
    """
    cmd = _build_docker_command(workdir, container_name, deps_volume or None)

    proc = subprocess.Popen(  # noqa: S603
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    timed_out = False
    stderr_text = ""
    try:
        _, stderr_text = proc.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        # 先杀容器（--rm 保证随后自动删除），再收割 docker CLI 进程本身
        subprocess.run(  # noqa: S603
            ["docker", "kill", container_name],
            check=False,
            capture_output=True,
            timeout=30,
        )
        try:
            _, stderr_text = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            stderr_text = ""

    if timed_out:
        summary = _summarize_stderr(stderr_text)
        raise SandboxTimeoutError(
            f"SANDBOX_TIMEOUT: 执行超过 {timeout_seconds:g}s，容器 {container_name} 已被强制终止",
            summary,
        )

    payload: dict | None = None
    result_file = workdir / "result.json"
    if result_file.is_file():
        try:
            payload = json.loads(result_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = None
    return payload, stderr_text or "", proc.returncode


def _summarize_stderr(stderr_text: str) -> str:
    """stderr 摘要：去空行后保留末尾若干字符（traceback 尾部最有诊断价值）。"""
    lines = [line for line in (stderr_text or "").splitlines() if line.strip()]
    summary = "\n".join(lines)[-_STDERR_SUMMARY_CHARS:]
    return summary


def _with_stderr_summary(error: str, stderr_summary: str) -> str:
    if stderr_summary:
        return f"{error}\n--- 子进程 stderr 摘要 ---\n{stderr_summary}"
    return error


def _persist_artifact(chart_png_path: str | None, workdir: Path, artifacts_dir: Path) -> str | None:
    """把子进程产出的图表 PNG 迁出临时目录（临时目录随后会被整体删除）。

    安全起见只接受位于工作目录内的路径，防止把宿主任意文件拷进 reports。
    """
    if not chart_png_path or not artifacts_dir:
        return chart_png_path if chart_png_path else None
    try:
        src = Path(chart_png_path)
        if not src.is_absolute():
            src = workdir / src
        resolved = src.resolve()
        if workdir.resolve() not in resolved.parents or not resolved.is_file():
            return None
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        dest = artifacts_dir / f"sandbox_chart_{uuid.uuid4().hex[:12]}.png"
        shutil.copyfile(resolved, dest)
        return str(dest)
    except OSError:
        return None


def safe_execute_pandas(
    code: str,
    df: pd.DataFrame,
    timeout_seconds: float | None = None,
    artifacts_dir: str | None = None,
) -> dict:
    """在隔离沙箱（子进程或容器）中执行 Pandas 代码。

    流程与防护边界见模块 docstring。同步接口：

    参数:
        code: 用户分析代码，须给全局变量 ``result`` 赋值作为结果；
              可选设置 ``chart_png_path`` 变量传递图表 PNG 路径。
        df: 输入 DataFrame（复制到临时工作目录的 input.csv 注入）。
        timeout_seconds: 墙钟超时；缺省读 settings.SANDBOX_TIMEOUT_SECONDS。
        artifacts_dir: 提供时把产出的图表 PNG 迁入该持久目录。

    返回:
        {"result": JSON 化结果或 None, "error": "" 或错误消息,
         "error_type": "" / SANDBOX_TIMEOUT / SANDBOX_ERROR,
         "stderr_summary": 执行体 stderr 尾部摘要, "chart_png_path": 图表路径或 None}
        异常代码的错误消息附带 stderr 摘要（含 traceback 尾部）。
    """
    timeout = float(settings.SANDBOX_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds)

    def _failure(error: str, error_type: str = ERROR_EXECUTION, stderr_summary: str = "") -> dict:
        return {
            "result": None,
            "error": _with_stderr_summary(error, stderr_summary) if error_type != ERROR_TIMEOUT else error,
            "error_type": error_type,
            "stderr_summary": stderr_summary,
            "chart_png_path": None,
        }

    # ── 第一道门：静态 AST 校验（语法错误 / dunder 反射逃逸直接拒绝，不启动执行体）──
    try:
        _validate_sandbox_code(code)
    except SyntaxError as exc:
        return _failure(f"SyntaxError: {exc}")
    except ValueError as exc:  # ast.parse 对含空字节等输入抛 ValueError
        return _failure(f"ValueError: {exc}")
    except NameError as exc:
        return _failure(f"NameError: {exc}")

    # ── 第二道门：选择隔离执行器。docker 模式准备失败一律回退 subprocess 并 warning ──
    runner: Callable[..., tuple[dict | None, str, int | None]] = _run_child
    run_kwargs: dict = {}
    use_docker = False
    if settings.SANDBOX_MODE == "docker":
        image = settings.SANDBOX_DOCKER_IMAGE
        if not _docker_cli_available():
            logger.warning("SANDBOX_MODE=docker 但 docker 引擎不可用，本次回退 subprocess 模式")
        elif not _ensure_docker_image(image):
            pass  # 镜像缺失且 pull 失败：_ensure_docker_image 已记录 warning
        else:
            deps_volume = _resolve_docker_deps_volume(image)
            if deps_volume is None:
                logger.warning("沙箱镜像 %s 缺少 pandas 且依赖卷准备失败，本次回退 subprocess 模式", image)
            else:
                use_docker = True
                runner = _run_docker
                run_kwargs = {"container_name": f"aiwb_sandbox_{uuid.uuid4().hex[:12]}", "deps_volume": deps_volume}

    workdir = Path(tempfile.mkdtemp(prefix="aiwb_sandbox_"))
    try:
        _write_workdir(workdir, df=df, code=code, timeout_seconds=timeout, include_child_script=use_docker)
        try:
            payload, stderr_text, returncode = runner(workdir, timeout, **run_kwargs)
        except SandboxTimeoutError as exc:
            # 超时错误以 SANDBOX_TIMEOUT 前缀 + error_type 字段双通道暴露
            return {
                "result": None,
                "error": str(exc),
                "error_type": ERROR_TIMEOUT,
                "stderr_summary": exc.stderr_summary,
                "chart_png_path": None,
            }

        stderr_summary = _summarize_stderr(stderr_text)

        # 执行体未按协议产出结果：硬崩溃 / OOM 击杀 / 解释器级故障
        if payload is None:
            label = "容器" if use_docker else "子进程"
            error = f"SANDBOX_ERROR: 沙箱{label}异常退出（exit={returncode}），未产出 result.json"
            return _failure(error, stderr_summary=stderr_summary)

        if payload.get("status") != "ok":
            error = f"{payload.get('error_type', 'UnknownError')}: {payload.get('error', '')}"
            return _failure(error, stderr_summary=stderr_summary)

        raw_chart_path = payload.get("chart_png_path")
        chart_png_path = _persist_artifact(raw_chart_path, workdir, Path(artifacts_dir)) if artifacts_dir else None

        return {
            "result": payload.get("result"),
            "error": "",
            "error_type": ERROR_OK,
            "stderr_summary": "",
            "chart_png_path": chart_png_path,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

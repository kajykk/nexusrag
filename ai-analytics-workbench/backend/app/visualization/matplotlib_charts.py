"""服务端图表渲染：使用 Matplotlib/Seaborn 生成 PNG。"""

import os
import time
from typing import Any

import matplotlib

matplotlib.use("Agg")  # 无 GUI 后端
import matplotlib.pyplot as plt
import pandas as pd

from app.config import settings

# 中文字体
plt.rcParams["font.sans-serif"] = ["Noto Sans CJK SC", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _ensure_reports_dir() -> str:
    reports_dir = settings.reports_abs_dir
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


def cleanup_old_charts(max_age_days: int) -> int:
    """删除超过保留期的 chart_*.png，返回清理数量（尽力而为，失败不抛出）。

    历史图表随分析次数无限累积；按 CHART_RETENTION_DAYS 定期回收。
    注意：清理后旧报告中的服务端图表将不可再下载——保留期需结合
    报告留存要求配置（设为 0 可禁用）。
    """
    if max_age_days <= 0:
        return 0
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    try:
        reports_dir = settings.reports_abs_dir
        if not os.path.isdir(reports_dir):
            return 0
        for name in os.listdir(reports_dir):
            path = os.path.join(reports_dir, name)
            if not name.startswith("chart_") or not name.endswith(".png"):
                continue
            try:
                if os.path.getmtime(path) < cutoff:
                    os.unlink(path)
                    removed += 1
            except OSError:
                continue
    except OSError:
        return removed
    return removed


def render_chart(
    result: Any,
    chart_type: str,
    analysis_id: int,
    chart_config: dict | None = None,
) -> str:
    """根据分析结果与图表类型渲染 PNG，返回相对路径。

    参数:
        result: 分析结果（dict / list / DataFrame）
        chart_type: bar / line / pie / scatter / table
        analysis_id: 用于生成文件名
        chart_config: 额外配置（title 等）

    返回:
        相对路径，如 `reports/chart_42.png`
    """
    chart_config = chart_config or {}
    title = chart_config.get("title", f"分析结果 #{analysis_id}")
    reports_dir = _ensure_reports_dir()
    # 带时间戳后缀：重跑同一分析不再静默覆盖旧图（旧报告引用的文件内容会变）
    filename = f"chart_{analysis_id}_{int(time.time())}.png"
    filepath = os.path.join(reports_dir, filename)

    df = _to_dataframe(result)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=120)
    try:
        if df is None or df.empty or chart_type == "table":
            _render_table(ax, df, title)
        elif chart_type == "bar":
            _render_bar(ax, df, chart_config)
        elif chart_type == "line":
            _render_line(ax, df, chart_config)
        elif chart_type == "pie":
            _render_pie(ax, df, chart_config)
        elif chart_type == "scatter":
            _render_scatter(ax, df, chart_config)
        else:
            _render_table(ax, df, title)

        fig.tight_layout()
        fig.savefig(filepath, bbox_inches="tight")
    finally:
        # 渲染异常时也必须关闭 figure，否则 pyplot 全局状态泄漏内存
        plt.close(fig)
    return f"reports/{filename}"


def _to_dataframe(result: Any) -> pd.DataFrame | None:
    """将分析结果转为 DataFrame。"""
    if result is None:
        return None
    if isinstance(result, pd.DataFrame):
        return result
    if isinstance(result, dict):
        # 若 dict 的 value 都是标量，转为单行
        if all(not isinstance(v, list | dict) for v in result.values()):
            return pd.DataFrame([result])
        return pd.DataFrame(result)
    if isinstance(result, list):
        if not result:
            return pd.DataFrame()
        if isinstance(result[0], dict):
            return pd.DataFrame(result)
        return pd.DataFrame({"value": result})
    return pd.DataFrame({"value": [result]})


def _render_table(ax: plt.Axes, df: pd.DataFrame | None, title: str) -> None:
    ax.axis("off")
    ax.set_title(title, fontsize=14, pad=12)
    if df is None or df.empty:
        ax.text(0.5, 0.5, "无数据", ha="center", va="center", fontsize=12)
        return
    data = df.head(20).values.tolist()
    cols = list(df.columns)
    table = ax.table(cellText=data, colLabels=cols, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)


def _render_bar(ax: plt.Axes, df: pd.DataFrame, config: dict) -> None:
    ax.set_title(config.get("title", ""), fontsize=14)
    df.plot(kind="bar", ax=ax, legend=True)
    ax.set_xlabel(config.get("xLabel", ""))
    ax.set_ylabel(config.get("yLabel", ""))
    ax.tick_params(axis="x", rotation=30)


def _render_line(ax: plt.Axes, df: pd.DataFrame, config: dict) -> None:
    ax.set_title(config.get("title", ""), fontsize=14)
    df.plot(kind="line", ax=ax, marker="o", legend=True)
    ax.set_xlabel(config.get("xLabel", ""))
    ax.set_ylabel(config.get("yLabel", ""))


def _render_pie(ax: plt.Axes, df: pd.DataFrame, config: dict) -> None:
    ax.set_title(config.get("title", ""), fontsize=14)
    if df.shape[1] >= 2:
        labels = df.iloc[:, 0].astype(str).tolist()
        values = df.iloc[:, 1].tolist()
        ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
        ax.axis("equal")


def _render_scatter(ax: plt.Axes, df: pd.DataFrame, config: dict) -> None:
    ax.set_title(config.get("title", ""), fontsize=14)
    if df.shape[1] >= 2:
        ax.scatter(df.iloc[:, 0], df.iloc[:, 1])
        ax.set_xlabel(str(df.columns[0]))
        ax.set_ylabel(str(df.columns[1]))

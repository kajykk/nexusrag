"""报告服务：生成 Markdown 报告并导出 PDF。"""

import json
import os
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.logging_config import get_logger
from app.models import Report, User
from app.services.analysis_service import get_analysis
from app.services.ownership import is_visible

logger = get_logger(__name__)


def build_markdown(db: Session, analysis_id: int, title: str = "数据分析报告", owner: User | None = None) -> Report:
    """根据分析结果生成 Markdown 报告并保存。

    owner 提供时校验分析归属（无权访问视为不存在），报告继承分析的归属。
    """
    analysis = get_analysis(db, analysis_id, owner)
    if not analysis:
        raise ValueError("分析任务不存在")

    result_data = json.loads(analysis.result_data or "{}")
    summary = result_data.get("summary", "")
    result = result_data.get("result")

    md_parts = [
        f"# {title}",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. 分析需求",
        "",
        analysis.question,
        "",
        "## 2. 分析思路与结论",
        "",
        summary or "（无）",
        "",
        "## 3. 分析代码",
        "",
        f"```python\n{analysis.generated_code}\n```",
        "",
        "## 4. 分析结果",
        "",
        _format_result(result),
        "",
    ]

    if analysis.chart_image and os.path.exists(analysis.chart_image):
        md_parts += [
            "## 5. 可视化图表",
            "",
            f"![分析图表](/{analysis.chart_image})",
            "",
        ]

    if analysis.error_message:
        md_parts += ["## ⚠️ 错误信息", "", analysis.error_message, ""]

    content_md = "\n".join(md_parts)

    # 覆盖已有报告或新建（继承分析任务归属）。
    # NULL 属主分析过渡期只读：普通用户不可据其生成/覆盖报告（防止"认领"）
    from app.services.ownership import can_mutate

    if not can_mutate(analysis, owner):
        raise ValueError("无权对该分析生成报告")

    report = db.query(Report).filter(Report.analysis_id == analysis_id).first()
    if report:
        report.title = title
        report.content_md = content_md
    else:
        report = Report(
            analysis_id=analysis_id,
            title=title,
            content_md=content_md,
            owner_id=analysis.owner_id if analysis.owner_id is not None else (owner.id if owner else None),
        )
        db.add(report)
    db.commit()
    db.refresh(report)
    logger.info("report.built", extra={"report_id": report.id, "analysis_id": analysis_id})
    return report


def _format_result(result) -> str:
    """将结果转为 Markdown 表格或文本。"""
    if result is None:
        return "（无结果）"
    if isinstance(result, list) and result and isinstance(result[0], dict):
        return _list_to_markdown_table(result)
    if isinstance(result, dict):
        # 若是 {列: [值]} 形式
        if result and all(isinstance(v, list) for v in result.values()):
            cols = list(result.keys())
            rows = list(zip(*[result[c] for c in cols], strict=False))
            return _table_to_markdown(cols, rows)
        return _dict_to_markdown(result)
    return f"```\n{result}\n```"


def _list_to_markdown_table(items: list[dict]) -> str:
    if not items:
        return "（空）"
    cols = list(items[0].keys())
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = ["| " + " | ".join(str(item.get(c, "")) for c in cols) + " |" for item in items[:50]]
    return "\n".join([header, sep, *rows])


def _table_to_markdown(cols: list, rows: list) -> str:
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = ["| " + " | ".join(str(c) for c in row) + " |" for row in rows[:50]]
    return "\n".join([header, sep, *body])


def _dict_to_markdown(d: dict) -> str:
    lines = [f"- **{k}**: {v}" for k, v in d.items()]
    return "\n".join(lines)


def _local_only_url_fetcher(url: str, *args: object, **kwargs: object):  # noqa: ANN002, ANN003
    """WeasyPrint 资源抓取白名单：仅允许相对路径 / file:// 本地文件。

    用户可控内容（标题/问题/LLM 输出）可能包含外链 <img>，若不拦截，
    导出 PDF 时服务器会代为请求任意 URL（SSRF，含云元数据地址）。
    """
    from urllib.parse import urlparse

    from weasyprint import default_url_fetcher

    scheme = urlparse(url).scheme
    if scheme in ("", "file"):
        return default_url_fetcher(url, *args, **kwargs)
    logger.warning("report.pdf_blocked_external_resource", extra={"report_url": url[:200]})
    raise ValueError(f"禁止在 PDF 中引用外部资源: {url[:120]}")


def export_pdf(db: Session, report_id: int, user: User | None = None) -> str:
    """将 Markdown 报告导出为 PDF，返回相对路径；user 提供时校验归属。"""
    import markdown
    from weasyprint import HTML

    report = db.get(Report, report_id)
    if not report or not is_visible(report, user):
        raise ValueError("报告不存在")

    reports_dir = settings.reports_abs_dir
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f"report_{report_id}.pdf")

    html_body = markdown.markdown(report.content_md, extensions=["tables", "fenced_code"])
    html_doc = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: "Noto Sans CJK SC", sans-serif; padding: 32px; line-height: 1.6; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
  th {{ background: #f5f5f5; }}
  pre {{ background: #f6f8fa; padding: 12px; border-radius: 4px; overflow-x: auto; }}
  code {{ font-family: Consolas, monospace; }}
  img {{ max-width: 100%; }}
</style>
</head>
<body>{html_body}</body>
</html>"""

    HTML(string=html_doc, url_fetcher=_local_only_url_fetcher).write_pdf(pdf_path)
    report.pdf_path = f"reports/report_{report_id}.pdf"
    db.commit()
    logger.info("report.exported_pdf", extra={"report_id": report_id, "pdf_path": report.pdf_path})
    return report.pdf_path

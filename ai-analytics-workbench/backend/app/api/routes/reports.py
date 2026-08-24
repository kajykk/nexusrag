"""报告路由：生成、查询、导出 PDF（P0 升级：写操作需认证 + 路径遍历防护）。

P1 安全升级：所有端点按 owner_id 过滤（见 app.services.ownership），
防止越权访问他人报告（IDOR）。
"""

import os
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.models import Report, User
from app.schemas.report import ReportCreate, ReportOut
from app.services import build_markdown, export_pdf
from app.services.ownership import apply_visible, is_visible

router = APIRouter(prefix="/reports", tags=["reports"])

# 安全：限制 pdf_path 形如 reports/report_<int>.pdf，防止路径遍历
_PDF_PATH_RE = re.compile(r"^reports/report_\d+\.pdf$")


@router.get("", response_model=list[ReportOut])
def list_all(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ReportOut]:
    """仅返回当前用户可见的报告。"""
    items = apply_visible(db.query(Report), Report, user).order_by(Report.created_at.desc()).all()
    return [ReportOut.model_validate(r) for r in items]


@router.post("", response_model=ReportOut, status_code=201)
def create(
    req: ReportCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ReportOut:
    """根据分析结果生成 Markdown 报告（校验分析归属）。"""
    try:
        report = build_markdown(db, req.analysis_id, req.title, owner=user)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return ReportOut.model_validate(report)


def _get_visible_report(db: Session, report_id: int, user: User) -> Report | None:
    """获取对 user 可见的报告；不可见视为不存在。"""
    report = db.get(Report, report_id)
    if not report or not is_visible(report, user):
        return None
    return report


@router.get("/{report_id}", response_model=ReportOut)
def detail(
    report_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ReportOut:
    report = _get_visible_report(db, report_id, user)
    if not report:
        raise HTTPException(404, "报告不存在")
    return ReportOut.model_validate(report)


@router.post("/{report_id}/export-pdf", response_model=dict)
def export(
    report_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """导出 PDF，返回相对路径（校验报告归属）。"""
    try:
        pdf_path = export_pdf(db, report_id, user)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return {"pdf_path": pdf_path}


@router.get("/{report_id}/download")
def download(
    report_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> FileResponse:
    """下载 PDF 文件（校验报告归属）。"""
    report = _get_visible_report(db, report_id, user)
    if not report or not report.pdf_path:
        raise HTTPException(404, "PDF 尚未生成")

    # 安全：校验 pdf_path 形如 reports/report_<int>.pdf，防止路径遍历
    if not _PDF_PATH_RE.match(report.pdf_path):
        raise HTTPException(500, "PDF 路径格式异常")

    abs_path = os.path.join(os.getcwd(), report.pdf_path)
    # 二次校验：解析后的绝对路径必须在 reports 目录内
    reports_root = os.path.abspath(os.path.join(os.getcwd(), "reports"))
    abs_path_resolved = os.path.abspath(abs_path)
    if not abs_path_resolved.startswith(reports_root + os.sep):
        raise HTTPException(500, "PDF 路径越界")

    if not os.path.exists(abs_path_resolved):
        raise HTTPException(404, "PDF 文件不存在")
    return FileResponse(
        abs_path_resolved,
        media_type="application/pdf",
        filename=f"report_{report_id}.pdf",
    )

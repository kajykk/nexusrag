"""分析任务路由：创建、查询、列表、图表下发（P0 升级：写操作需认证 + Pydantic 序列化）。

P1 安全升级：所有端点按 owner_id 过滤（见 app.services.ownership），
创建时校验数据集归属，防止越权访问他人任务（IDOR）。
P2 安全升级：图表文件由公开静态挂载改为认证端点按归属下发，
路径白名单校验防止遍历。
"""

import json
import os
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.celery_app import run_analysis_task
from app.config import settings
from app.models import Analysis, User
from app.schemas.analysis import AnalysisCreate, AnalysisOut
from app.services import create_analysis, get_analysis, list_analyses

router = APIRouter(prefix="/analyses", tags=["analyses"])

# 安全：限制 chart_image 形如 reports/chart_<int>.png（或沙箱产物 chart_<int>_*.png），
# 防止路径遍历
_CHART_PATH_RE = re.compile(r"^reports/chart_\d+[\w.-]*\.png$")


@router.post("", response_model=dict)
def create(
    req: AnalysisCreate,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """创建分析任务并投递到 Celery 异步执行（校验数据集归属）。"""
    try:
        analysis = create_analysis(db, req.dataset_id, req.question, owner=user)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    run_analysis_task.delay(analysis.id)
    return {"analysis_id": analysis.id, "status": analysis.status}


@router.get("", response_model=list[AnalysisOut])
def list_all(
    dataset_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[AnalysisOut]:
    """仅返回当前用户可见的分析任务（支持 limit/offset 分页，默认 100 条）。"""
    try:
        items = list_analyses(db, dataset_id, user, limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return [_serialize(a) for a in items]


@router.get("/{analysis_id}", response_model=AnalysisOut)
def detail(
    analysis_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AnalysisOut:
    a = get_analysis(db, analysis_id, user)
    if not a:
        raise HTTPException(404, "分析任务不存在")
    return _serialize(a, full=True)


@router.get("/{analysis_id}/chart")
def chart(
    analysis_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> FileResponse:
    """下载分析图表 PNG（校验任务归属，替代原匿名静态挂载）。"""
    a = get_analysis(db, analysis_id, user)
    if not a:
        raise HTTPException(404, "分析任务不存在")
    if not a.chart_image:
        raise HTTPException(404, "图表尚未生成")

    # 安全：路径白名单 + 双重越界校验（与 PDF 下载同强度）
    if not _CHART_PATH_RE.match(a.chart_image):
        raise HTTPException(500, "图表路径格式异常")

    abs_path = os.path.abspath(
        os.path.join(settings.reports_abs_dir, os.path.basename(a.chart_image))
    )
    reports_root = settings.reports_abs_dir
    if not abs_path.startswith(reports_root + os.sep):
        raise HTTPException(500, "图表路径越界")

    if not os.path.exists(abs_path):
        raise HTTPException(404, "图表文件不存在")
    return FileResponse(abs_path, media_type="image/png")


def _serialize(a: Analysis, full: bool = False) -> AnalysisOut:
    """将 ORM 模型转为 AnalysisOut，处理 JSON 字段反序列化。"""
    data = {
        "id": a.id,
        "dataset_id": a.dataset_id,
        "question": a.question,
        "status": a.status,
        "code_type": a.code_type,
        "chart_image": a.chart_image,
        "error_message": a.error_message,
        "created_at": a.created_at,
        "completed_at": a.completed_at,
        "generated_code": a.generated_code if full else "",
    }
    try:
        data["result_data"] = json.loads(a.result_data or "{}") if full else {}
    except json.JSONDecodeError:
        data["result_data"] = {}
    try:
        data["chart_config"] = json.loads(a.chart_config or "{}") if full else {}
    except json.JSONDecodeError:
        data["chart_config"] = {}
    return AnalysisOut.model_validate(data)

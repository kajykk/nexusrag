"""分析任务路由：创建、查询、列表（P0 升级：写操作需认证 + Pydantic 序列化）。

P1 安全升级：所有端点按 owner_id 过滤（见 app.services.ownership），
创建时校验数据集归属，防止越权访问他人任务（IDOR）。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.celery_app import run_analysis_task
from app.models import Analysis, User
from app.schemas.analysis import AnalysisCreate, AnalysisOut
from app.services import create_analysis, get_analysis, list_analyses

router = APIRouter(prefix="/analyses", tags=["analyses"])


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
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[AnalysisOut]:
    """仅返回当前用户可见的分析任务。"""
    items = list_analyses(db, dataset_id, user)
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


def _serialize(a: Analysis, full: bool = False) -> AnalysisOut:
    """将 ORM 模型转为 AnalysisOut，处理 JSON 字段反序列化。"""
    import json

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

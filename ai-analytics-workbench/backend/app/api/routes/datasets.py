"""数据集路由：上传、列表、详情、删除（P0 升级：写操作需认证）。

P1 安全升级：所有端点按 owner_id 过滤（见 app.services.ownership），
防止越权访问他人数据集（IDOR）。
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.config import settings
from app.models import User
from app.schemas.dataset import DatasetDetail, DatasetOut
from app.services import (
    delete_dataset,
    get_dataset_detail,
    list_datasets,
    upload_dataset,
)
from app.services.dataset_service import ALLOWED_EXTENSIONS

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _validate_file_extension(filename: str | None) -> None:
    """路由层扩展名白名单校验（与 service 层形成纵深防御）。"""
    if not filename or "." not in filename:
        raise HTTPException(400, "文件名缺少扩展名")
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(400, f"不支持的文件类型: .{ext}，仅支持: {allowed}")


@router.post("/upload", response_model=DatasetOut, status_code=201)
def upload(
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
) -> DatasetOut:
    """上传 CSV/Excel 文件并自动入库 PostgreSQL（归属当前用户）。

    同步 ``def`` 路由：解析/写库是重 CPU/IO 操作，FastAPI 会自动放入
    线程池执行，避免阻塞事件循环拖垮全部并发请求。
    """
    # 路由层扩展名校验：在读取内容前提前拒绝非法文件
    _validate_file_extension(file.filename)
    # 大小预检：Starlette 已解析的分区大小 + Content-Length 双重提前拒绝，
    # 避免先整读入内存才发现超限
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise HTTPException(413, f"文件超过 {settings.MAX_UPLOAD_SIZE_MB}MB 限制")
    try:
        dataset = upload_dataset(db, file, name, description, owner=user)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return DatasetOut.model_validate(dataset)


@router.get("", response_model=list[DatasetOut])
def list_all(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[DatasetOut]:
    """仅返回当前用户可见的数据集（支持 limit/offset 分页，默认 100 条）。"""
    try:
        items = list_datasets(db, user, limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return [DatasetOut.model_validate(d) for d in items]


@router.get("/{dataset_id}", response_model=DatasetDetail)
def detail(
    dataset_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DatasetDetail:
    detail_data = get_dataset_detail(db, dataset_id, user)
    if not detail_data:
        raise HTTPException(404, "数据集不存在")
    return DatasetDetail.model_validate(detail_data)


@router.delete("/{dataset_id}")
def remove(
    dataset_id: int,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    ok = delete_dataset(db, dataset_id, user)
    if not ok:
        raise HTTPException(404, "数据集不存在")
    return {"deleted": True}

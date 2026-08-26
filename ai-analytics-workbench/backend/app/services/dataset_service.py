"""数据集服务：上传、入库、查询。"""

import json
import secrets

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.logging_config import get_logger
from app.models import Dataset, User
from app.services.ownership import apply_visible, is_visible
from app.utils import (
    dataframe_to_pg,
    drop_table_if_exists,
    get_table_preview,
    infer_dataframe_schema,
)

logger = get_logger(__name__)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


def _read_dataframe(file: UploadFile) -> tuple[pd.DataFrame, str]:
    """根据扩展名读取 DataFrame，返回 (df, file_type)。"""
    filename = file.filename or "upload.csv"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv"
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: .{ext}，仅支持 {ALLOWED_EXTENSIONS}")

    content = file.file.read()
    if ext == "csv":
        df = pd.read_csv(pd.io.common.BytesIO(content))
    elif ext == "xlsx":
        df = pd.read_excel(pd.io.common.BytesIO(content), engine="openpyxl")
    else:  # xls
        df = pd.read_excel(pd.io.common.BytesIO(content), engine="xlrd")
    return df, ext


def _generate_table_name(dataset_id: int) -> str:
    """生成唯一的物理表名：ds_<id>_<6位随机>。"""
    return f"ds_{dataset_id}_{secrets.token_hex(3)}"


def upload_dataset(db: Session, file: UploadFile, name: str, description: str = "", owner: User | None = None) -> Dataset:
    """上传文件并入库 PostgreSQL。

    流程：读取 -> 创建 Dataset 记录（随机占位表名，规避唯一约束冲突）->
    建表入库 -> 更新统计信息。任一步失败时补偿删除元数据与半成品物理表，
    避免孤儿记录污染后续上传。
    """
    df, file_type = _read_dataframe(file)
    if df.empty:
        raise ValueError("文件内容为空")

    # 用随机占位表名创建记录以拿到 id（"placeholder" 固定值会触发
    # table_name 唯一约束：一次失败后所有后续上传永久 500）
    dataset = Dataset(
        name=name,
        original_filename=file.filename or name,
        table_name=f"ds_pending_{secrets.token_hex(8)}",
        file_type=file_type,
        row_count=0,
        column_count=0,
        columns_schema="[]",
        description=description,
        owner_id=owner.id if owner else None,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # 生成表名并入库
    table_name = _generate_table_name(dataset.id)
    try:
        dataframe_to_pg(df, table_name)
        schema = infer_dataframe_schema(df)
        dataset.table_name = table_name
        dataset.row_count = int(len(df))
        dataset.column_count = int(df.shape[1])
        dataset.columns_schema = json.dumps(schema, ensure_ascii=False)
        db.commit()
        db.refresh(dataset)
    except Exception:
        # 补偿事务：回滚并清理孤儿元数据 / 半成品物理表
        db.rollback()
        try:
            drop_table_if_exists(table_name)
        except Exception:  # noqa: BLE001
            logger.warning("dataset.compensation_drop_failed", extra={"table_name": table_name}, exc_info=True)
        db.delete(dataset)
        db.commit()
        raise
    logger.info(
        "dataset.uploaded",
        extra={
            "dataset_id": dataset.id,
            "table_name": table_name,
            "rows": dataset.row_count,
            "cols": dataset.column_count,
        },
    )
    return dataset


def list_datasets(
    db: Session, user: User | None = None, limit: int = 100, offset: int = 0
) -> list[Dataset]:
    """列出当前用户可见的数据集（按 owner 过滤，管理员可见全部；支持分页）。"""
    if limit < 1 or limit > 500:
        raise ValueError("limit 应在 1..500 之间")
    if offset < 0:
        raise ValueError("offset 不能为负")
    q = apply_visible(db.query(Dataset), Dataset, user)
    return q.order_by(Dataset.created_at.desc()).limit(limit).offset(offset).all()


def get_dataset(db: Session, dataset_id: int, user: User | None = None) -> Dataset | None:
    """获取数据集；user 提供时校验归属，不可见视为不存在。"""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        return None
    if not is_visible(dataset, user):
        return None
    return dataset


def get_dataset_detail(db: Session, dataset_id: int, user: User | None = None) -> dict | None:
    """获取数据集详情（含 schema 与预览）；无权访问时返回 None。"""
    dataset = get_dataset(db, dataset_id, user)
    if not dataset:
        return None
    try:
        preview = get_table_preview(dataset.table_name, limit=5)
    except Exception:  # noqa: BLE001
        logger.warning(
            "dataset.preview_failed", extra={"dataset_id": dataset_id, "table_name": dataset.table_name}, exc_info=True
        )
        preview = []
    return {
        "id": dataset.id,
        "name": dataset.name,
        "original_filename": dataset.original_filename,
        "file_type": dataset.file_type,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "created_at": dataset.created_at,
        "description": dataset.description,
        "columns_schema": json.loads(dataset.columns_schema or "[]"),
        "preview": preview,
    }


def delete_dataset(db: Session, dataset_id: int, user: User | None = None) -> bool:
    """删除数据集及其物理表；user 提供时校验归属。

    NULL 属主行过渡期只读：普通用户不可删除（管理员可）。
    """
    dataset = get_dataset(db, dataset_id, user)
    if not dataset:
        return False
    from app.services.ownership import can_mutate

    if not can_mutate(dataset, user):
        logger.warning(
            "dataset.mutate_denied_readonly_row",
            extra={"dataset_id": dataset_id, "user_id": getattr(user, "id", None)},
        )
        return False

    # 先提交元数据删除，再尽力而为 drop 物理表：
    # 顺序颠倒会在 commit 失败时留下指向已删表的"僵尸行"，或 drop 失败时
    # 元数据照删导致物理表成为无主存储。drop 失败仅告警，由后台 GC 兜底。
    table_name = dataset.table_name
    db.delete(dataset)
    db.commit()
    try:
        drop_table_if_exists(table_name)
    except Exception:  # noqa: BLE001
        logger.warning(
            "dataset.drop_table_failed",
            extra={"dataset_id": dataset_id, "table_name": table_name},
            exc_info=True,
        )
    logger.info("dataset.deleted", extra={"dataset_id": dataset_id})
    return True

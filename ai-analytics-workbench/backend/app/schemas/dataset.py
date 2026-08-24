"""数据集相关的 Pydantic 模型。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ColumnInfo(BaseModel):
    """数据集列信息。"""

    name: str
    dtype: str
    sample: list[Any] = Field(default_factory=list)
    null_count: int = 0
    unique_count: int = 0


class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class DatasetCreate(DatasetBase):
    pass


class DatasetOut(BaseModel):
    """数据集列表项。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    original_filename: str
    file_type: str
    row_count: int
    column_count: int
    created_at: datetime


class DatasetDetail(DatasetOut):
    """数据集详情（含列信息与预览）。"""

    columns_schema: list[ColumnInfo] = Field(default_factory=list)
    preview: list[dict[str, Any]] = Field(default_factory=list)
    description: str = ""

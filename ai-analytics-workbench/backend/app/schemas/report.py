"""报告相关的 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReportCreate(BaseModel):
    analysis_id: int
    title: str = "数据分析报告"


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_id: int
    title: str
    content_md: str
    pdf_path: str
    created_at: datetime

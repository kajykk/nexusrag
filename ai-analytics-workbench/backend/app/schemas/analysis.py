"""分析任务相关的 Pydantic 模型。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AnalysisCreate(BaseModel):
    """创建分析任务。"""

    dataset_id: int
    question: str = Field(..., min_length=1, description="自然语言分析需求")


class AnalysisOut(BaseModel):
    """分析任务输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    question: str
    status: str
    code_type: str = "python"
    generated_code: str = ""
    result_data: dict[str, Any] = Field(default_factory=dict)
    chart_config: dict[str, Any] = Field(default_factory=dict)
    chart_image: str = ""
    error_message: str = ""
    created_at: datetime
    completed_at: datetime | None = None


class AnalysisResult(BaseModel):
    """LLM 生成结果的结构（内部使用）。"""

    code_type: str = "python"
    code: str
    chart_type: str = "table"
    chart_config: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""


class WSProgressMessage(BaseModel):
    """WebSocket 推送的进度消息。"""

    analysis_id: int
    stage: str = Field(..., description="queued/running/succeeded/failed")
    progress: int = Field(0, ge=0, le=100)
    message: str = ""
    data: dict[str, Any] | None = None

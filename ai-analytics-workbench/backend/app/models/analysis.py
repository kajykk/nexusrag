"""分析任务 ORM 模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Analysis(Base):
    """单次自然语言分析任务。

    状态机：pending -> running -> succeeded / failed
    """

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="用户的自然语言分析需求")
    owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="归属用户"
    )
    status: Mapped[str] = mapped_column(String(16), default="pending", comment="pending/running/succeeded/failed")
    code_type: Mapped[str] = mapped_column(String(16), default="python", comment="python/sql")
    generated_code: Mapped[str] = mapped_column(Text, default="", comment="LLM 生成的代码")
    result_data: Mapped[str] = mapped_column(Text, default="{}", comment="执行结果 JSON")
    chart_config: Mapped[str] = mapped_column(Text, default="{}", comment="前端 ECharts 配置 JSON")
    chart_image: Mapped[str] = mapped_column(String(255), default="", comment="服务端渲染图表相对路径")
    error_message: Mapped[str] = mapped_column(Text, default="", comment="失败原因")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Analysis #{self.id} ds={self.dataset_id} {self.status}>"

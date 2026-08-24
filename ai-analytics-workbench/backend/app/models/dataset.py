"""数据集 ORM 模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Dataset(Base):
    """上传的数据集元信息。

    每条记录对应一张 PostgreSQL 物理表（table_name），
    表名形如 `ds_<id>_<短随机>`，避免与系统表冲突。
    """

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="数据集显示名")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    table_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, comment="入库后的物理表名")
    file_type: Mapped[str] = mapped_column(String(16), nullable=False, comment="csv/xlsx/xls")
    row_count: Mapped[int] = mapped_column(Integer, default=0, comment="行数")
    column_count: Mapped[int] = mapped_column(Integer, default=0, comment="列数")
    columns_schema: Mapped[str] = mapped_column(Text, nullable=False, default="[]", comment="列信息 JSON")
    description: Mapped[str] = mapped_column(Text, default="", comment="数据集描述")
    owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True, comment="归属用户"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Dataset #{self.id} {self.name} ({self.table_name})>"

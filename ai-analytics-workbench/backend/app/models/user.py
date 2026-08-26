"""用户 ORM 模型（P0 新增：认证机制）。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.utils.timeutil import utcnow


class User(Base):
    """平台用户。

    通过邮箱+密码注册，密码使用 bcrypt 哈希存储。
    JWT token 中携带 user.id 作为 subject。
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    def __repr__(self) -> str:
        return f"<User #{self.id} {self.email}>"

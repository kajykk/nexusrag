"""用户相关的 Pydantic 模型（P0 新增）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """注册请求。"""

    email: EmailStr
    name: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=6, max_length=64)


class UserLogin(BaseModel):
    """登录请求。"""

    email: EmailStr
    password: str = Field(..., min_length=1)


class UserOut(BaseModel):
    """用户信息输出。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    is_active: bool
    is_admin: bool
    created_at: datetime


class TokenOut(BaseModel):
    """登录成功返回的 token。"""

    access_token: str
    token_type: str = "bearer"
    user: UserOut

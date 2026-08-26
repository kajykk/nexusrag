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
    """登录/注册成功返回的 token 对。"""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    """刷新 access token 请求。"""

    refresh_token: str = Field(..., min_length=1)

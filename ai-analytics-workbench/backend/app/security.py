"""安全模块：密码哈希 + JWT token 签发与验证（P0 新增）。"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from app.config import settings


def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希。"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """签发 JWT access token。

    Args:
        subject: 用户 ID（字符串或整数）
        expires_delta: 自定义过期时间；默认使用 settings.JWT_EXPIRE_MINUTES

    Returns:
        编码后的 JWT 字符串
    """
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": uuid.uuid4().hex,  # 唯一 ID，为后续黑名单/吊销机制预留
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """签发 refresh token（type=refresh，默认有效期 settings.JWT_REFRESH_EXPIRE_MINUTES）。

    仅可用于 /auth/refresh 换取新 access token，不能直接访问业务 API
    （get_current_user / WS 鉴权均校验 type == "access"）。
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.JWT_REFRESH_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(UTC),
        "jti": uuid.uuid4().hex,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any] | None:
    """解析并验证 JWT token，失败返回 None。

    expected_type 提供时校验 token 类型（"access" / "refresh"），不匹配视为无效。
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except InvalidTokenError:
        return None
    if expected_type is not None and payload.get("type") != expected_type:
        return None
    return payload

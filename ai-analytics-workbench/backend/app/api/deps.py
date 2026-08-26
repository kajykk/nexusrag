"""API 公共依赖（P0 升级：添加认证依赖）。"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db
from app.logging_config import get_logger
from app.models import User
from app.security import decode_token

logger = get_logger(__name__)


def get_session(db: Session = Depends(get_db)) -> Session:
    """别名依赖，便于路由注入。"""
    return db


# OAuth2 password bearer：自动从 Authorization: Bearer <token> 提取 token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.JWT_TOKEN_URL, auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """解析 JWT token 并返回当前用户。

    用法：
        @router.post("/xxx")
        def handler(user: User = Depends(get_current_user)): ...
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        logger.debug("auth.no_token")
        raise credentials_exception

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        logger.warning("auth.invalid_token", extra={"reason": "decode_failed" if not payload else "wrong_type"})
        raise credentials_exception

    user_id_str = payload.get("sub")
    if not user_id_str:
        logger.warning("auth.invalid_token", extra={"reason": "missing_sub"})
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        logger.warning("auth.invalid_token", extra={"reason": "bad_sub", "sub": user_id_str})
        raise credentials_exception from None

    user = db.get(User, user_id)
    if not user or not user.is_active:
        logger.warning("auth.user_unavailable", extra={"user_id": user_id, "found": bool(user)})
        raise credentials_exception

    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """要求当前用户是管理员。"""
    if not user.is_admin:
        logger.warning("auth.admin_required", extra={"user_id": user.id})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user

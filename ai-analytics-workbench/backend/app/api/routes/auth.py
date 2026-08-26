"""认证路由：注册 / 登录 / 当前用户 / 演示账号（P0 新增）。

P2 安全升级：登录/注册接入每 IP 限流（防爆破）；demo 入口在生产环境禁用。
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.config import settings
from app.logging_config import get_logger
from app.models import User
from app.schemas.user import RefreshRequest, TokenOut, UserCreate, UserLogin, UserOut
from app.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.utils.ratelimit import auth_limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    """邮箱归一化：去空白 + 小写，避免大小写变体重复注册/登录失败。"""
    return email.strip().lower()


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_session)) -> TokenOut:
    """注册新账号并返回 token（限流：10 次/分钟/IP）。"""
    auth_limiter.check(request)
    email = _normalize_email(payload.email)
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        logger.info("auth.register_duplicate", extra={"email": email})
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册")

    user = User(
        email=email,
        name=payload.name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # 并发注册同一邮箱时 check-then-insert 会撞唯一约束，兜底转 409
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册") from None
    db.refresh(user)
    logger.info("auth.registered", extra={"user_id": user.id, "email": user.email})

    token = create_access_token(subject=user.id)
    refresh = create_refresh_token(subject=user.id)
    return TokenOut(access_token=token, refresh_token=refresh, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_session)) -> TokenOut:
    """邮箱+密码登录（限流：10 次/分钟/IP，防密码爆破）。"""
    auth_limiter.check(request)
    user = db.query(User).filter(User.email == _normalize_email(payload.email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning(
            "auth.login_failed",
            extra={"email": payload.email, "reason": "unknown_user" if not user else "bad_password"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        logger.warning("auth.login_failed", extra={"email": payload.email, "reason": "inactive", "user_id": user.id})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")

    token = create_access_token(subject=user.id)
    logger.info("auth.login_success", extra={"user_id": user.id})
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    """获取当前登录用户。"""
    return user


@router.post("/demo", response_model=TokenOut)
def demo_account(db: Session = Depends(get_session)) -> TokenOut:
    """演示账号一键登录（无密码、无需注册）。

    安全：默认 is_admin=False（降权）；仅当环境变量 DEMO_ALLOW_ADMIN=true
    时才授予管理员权限，防止公开演示入口被用于管理操作。
    生产环境（APP_ENV=production）直接禁用该入口，避免匿名铸币。
    """
    if settings.APP_ENV == "production":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    demo_email = "demo@analytics-workbench.dev"
    demo_is_admin = settings.DEMO_ALLOW_ADMIN
    user = db.query(User).filter(User.email == demo_email).first()
    if not user:
        user = User(
            email=demo_email,
            name="演示用户",
            hashed_password=hash_password("demo-no-password"),
            is_admin=demo_is_admin,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(subject=user.id)
    refresh = create_refresh_token(subject=user.id)
    return TokenOut(access_token=token, refresh_token=refresh, user=UserOut.model_validate(user))


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshRequest, db: Session = Depends(get_session)) -> TokenOut:
    """用 refresh token 换取新的 token 对。

    安全：仅接受 type=refresh 的 JWT（access/refresh 类型隔离，
    refresh token 不能直接访问业务 API）。当前实现不轮换 refresh，
    接入 Redis 黑名单后可在刷新时轮换并吊销旧 jti。
    """
    token_payload = decode_token(payload.refresh_token, expected_type="refresh")
    if not token_payload or not token_payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="refresh token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = int(token_payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh token 无效"
        ) from None

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")

    access = create_access_token(subject=user.id)
    new_refresh = create_refresh_token(subject=user.id)
    logger.info("auth.refreshed", extra={"user_id": user.id})
    return TokenOut(access_token=access, refresh_token=new_refresh, user=UserOut.model_validate(user))

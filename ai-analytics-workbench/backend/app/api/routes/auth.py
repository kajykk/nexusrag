"""认证路由：注册 / 登录 / 当前用户 / 演示账号（P0 新增）。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session
from app.config import settings
from app.logging_config import get_logger
from app.models import User
from app.schemas.user import TokenOut, UserCreate, UserLogin, UserOut
from app.security import create_access_token, hash_password, verify_password

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_session)) -> TokenOut:
    """注册新账号并返回 token。"""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        logger.info("auth.register_duplicate", extra={"email": payload.email})
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被注册")

    user = User(
        email=payload.email,
        name=payload.name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("auth.registered", extra={"user_id": user.id, "email": user.email})

    token = create_access_token(subject=user.id)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_session)) -> TokenOut:
    """邮箱+密码登录。"""
    user = db.query(User).filter(User.email == payload.email).first()
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
    """
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
    return TokenOut(access_token=token, user=UserOut.model_validate(user))

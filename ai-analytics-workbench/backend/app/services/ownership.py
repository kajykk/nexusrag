"""行级归属过滤助手（防 IDOR）。

可见性规则：
- user 为 None（服务内部调用/无认证上下文）：不过滤
- 管理员：可见全部
- 普通用户：仅 owner_id == 本人 的行；
  owner_id IS NULL 视为迁移前遗留的无主行，过渡期对所有登录用户**只读**可见，
  禁止修改/删除/据其派生资源（防止普通用户越权篡改或"认领"他人遗留数据）
  （alembic 0002 已回填既有行，生产环境正常情况下不存在 NULL 行）
"""

from sqlalchemy import or_

from app.models.user import User


def visible_clause(model, user: User | None):
    """返回 SQLAlchemy 过滤子句；None 表示不追加过滤。"""
    if user is None or user.is_admin:
        return None
    return or_(model.owner_id == user.id, model.owner_id.is_(None))


def apply_visible(query, model, user: User | None):
    """在 query 上应用归属过滤。"""
    clause = visible_clause(model, user)
    if clause is not None:
        query = query.filter(clause)
    return query


def is_visible(row, user: User | None) -> bool:
    """判断单行是否对 user 可见（含 NULL 属主行的过渡期只读可见）。"""
    if user is None or user.is_admin:
        return True
    return row.owner_id == user.id or row.owner_id is None


def can_mutate(row, user: User | None) -> bool:
    """判断 user 是否可以修改/删除该行，或据其创建派生资源。

    与可见性分离：NULL 属主行过渡期内只读——普通用户不可写/删，
    仅管理员可操作。user 为 None 表示服务内部调用，放行。
    """
    if user is None:
        return True
    if user.is_admin:
        return True
    return row.owner_id == user.id

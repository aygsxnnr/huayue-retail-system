import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import get_current_user, hash_password, require_roles
from ..database import get_db


router = APIRouter(tags=["用户与角色权限"])


ROLE_MENUS = {
    "系统管理员": ["dashboard", "pos", "products", "inventory", "members", "finance", "reports", "users", "operation_logs"],
    "总经理": ["dashboard", "reports", "finance"],
    "店长": ["pos", "inventory", "members"],
    "收银员": ["pos"],
    "库存管理员": ["inventory"],
    "营销专员": ["members"],
    "财务人员": ["finance"],
}


def write_operation_log(
    db: Session,
    current_user: models.User,
    module: str,
    action: str,
    target_type: str = "",
    target_id: str = "",
    before_data: str = "",
    after_data: str = "",
    remark: str = "",
) -> None:
    db.add(
        models.OperationLog(
            operator_id=current_user.id,
            operator_name=current_user.real_name,
            role=current_user.role,
            module=module,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_data=before_data,
            after_data=after_data,
            remark=remark,
        )
    )


@router.get("/api/roles", response_model=list[schemas.RoleOut])
def list_roles(current_user: models.User = Depends(get_current_user)):
    return [
        {
            "label": role,
            "value": role,
            "menus": menus,
        }
        for role, menus in ROLE_MENUS.items()
    ]


@router.get("/api/users", response_model=list[schemas.UserOut])
def list_users(
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("系统管理员")),
):
    query = db.query(models.User)

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                models.User.username.like(like),
                models.User.real_name.like(like),
                models.User.role.like(like),
                models.User.status.like(like),
            )
        )

    return query.order_by(models.User.id.asc()).limit(500).all()


@router.post("/api/users", response_model=schemas.UserOut)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("系统管理员")),
):
    exists = db.query(models.User).filter(models.User.username == payload.username).first()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    user = models.User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        real_name=payload.real_name,
        role=payload.role,
        store_id=payload.store_id,
        status=payload.status,
    )
    db.add(user)
    db.flush()

    write_operation_log(
        db,
        current_user,
        module="用户管理",
        action="新增用户",
        target_type="User",
        target_id=str(user.id),
        after_data=json.dumps(
            {
                "username": user.username,
                "real_name": user.real_name,
                "role": user.role,
                "status": user.status,
            },
            ensure_ascii=False,
        ),
    )

    db.commit()
    db.refresh(user)
    return user


@router.put("/api/users/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    payload: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("系统管理员")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    before = {
        "real_name": user.real_name,
        "role": user.role,
        "store_id": user.store_id,
        "status": user.status,
    }

    if payload.real_name is not None:
        user.real_name = payload.real_name
    if payload.role is not None:
        user.role = payload.role
    if payload.store_id is not None:
        user.store_id = payload.store_id
    if payload.status is not None:
        user.status = payload.status
    if payload.password:
        user.password_hash = hash_password(payload.password)

    after = {
        "real_name": user.real_name,
        "role": user.role,
        "store_id": user.store_id,
        "status": user.status,
    }

    write_operation_log(
        db,
        current_user,
        module="用户管理",
        action="编辑用户",
        target_type="User",
        target_id=str(user.id),
        before_data=json.dumps(before, ensure_ascii=False),
        after_data=json.dumps(after, ensure_ascii=False),
    )

    db.commit()
    db.refresh(user)
    return user


@router.put("/api/users/{user_id}/status", response_model=schemas.UserOut)
def update_user_status(
    user_id: int,
    payload: schemas.UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("系统管理员")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    before_status = user.status
    user.status = payload.status

    write_operation_log(
        db,
        current_user,
        module="用户管理",
        action="修改用户状态",
        target_type="User",
        target_id=str(user.id),
        before_data=json.dumps({"status": before_status}, ensure_ascii=False),
        after_data=json.dumps({"status": user.status}, ensure_ascii=False),
        remark=f"用户状态由 {before_status} 改为 {user.status}",
    )

    db.commit()
    db.refresh(user)
    return user

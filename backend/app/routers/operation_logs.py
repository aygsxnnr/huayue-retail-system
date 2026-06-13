from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import require_roles
from ..database import get_db


router = APIRouter(tags=["操作日志审计"])


@router.get("/api/operation-logs", response_model=list[schemas.OperationLogOut])
def list_operation_logs(
    module: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("系统管理员", "总经理")),
):
    query = db.query(models.OperationLog)

    if module:
        query = query.filter(models.OperationLog.module == module)

    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(
                models.OperationLog.operator_name.like(like),
                models.OperationLog.action.like(like),
                models.OperationLog.target_type.like(like),
                models.OperationLog.target_id.like(like),
                models.OperationLog.remark.like(like),
            )
        )

    return query.order_by(models.OperationLog.created_at.desc()).limit(limit).all()

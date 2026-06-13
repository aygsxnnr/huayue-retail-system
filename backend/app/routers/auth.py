from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth_utils import create_token, get_current_user, verify_password
from ..database import get_db


router = APIRouter(prefix="/api/auth", tags=["登录认证"])


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if user.status != "启用":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="当前用户已停用",
        )

    return {
        "token": create_token(user),
        "user": user,
    }


@router.get("/me", response_model=schemas.CurrentUserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "user": current_user,
    }


@router.post("/logout")
def logout():
    return {
        "message": "已退出登录",
    }

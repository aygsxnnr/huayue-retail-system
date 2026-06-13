from __future__ import annotations

import base64
import hashlib
import hmac
import time

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from . import models
from .database import get_db


SECRET_KEY = "huayue-retail-system-dev-secret"
TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 7


def hash_password(password: str) -> str:
    return hashlib.sha256(f"{SECRET_KEY}:{password}".encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def create_token(user: models.User) -> str:
    issued_at = int(time.time())
    payload = f"{user.id}:{issued_at}"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    raw = f"{payload}.{signature}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("utf-8").rstrip("=")


def parse_token(token: str) -> int:
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8")
        payload, signature = raw.rsplit(".", 1)
        expected_signature = hmac.new(
            SECRET_KEY.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("bad signature")

        user_id_text, issued_at_text = payload.split(":", 1)
        issued_at = int(issued_at_text)

        if int(time.time()) - issued_at > TOKEN_EXPIRE_SECONDS:
            raise ValueError("expired")

        return int(user_id_text)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效，请重新登录",
        )


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
        )

    token = authorization.replace("Bearer ", "", 1).strip()
    user_id = parse_token(token)

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if user.status != "启用":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已停用",
        )

    return user


def require_roles(*roles: str):
    def checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role == "系统管理员":
            return current_user

        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="当前角色无权限操作",
            )

        return current_user

    return checker

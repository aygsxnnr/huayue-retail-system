from datetime import datetime

from . import models
from .auth_utils import hash_password
from .database import Base, SessionLocal, engine


TEST_USERS = [
    {"username": "admin", "real_name": "系统管理员", "role": "系统管理员"},
    {"username": "manager", "real_name": "总经理", "role": "总经理"},
    {"username": "cashier", "real_name": "收银员", "role": "收银员"},
    {"username": "stock", "real_name": "库存管理员", "role": "库存管理员"},
    {"username": "marketing", "real_name": "营销专员", "role": "营销专员"},
    {"username": "finance", "real_name": "财务人员", "role": "财务人员"},
]


def main() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        first_store = db.query(models.Store).first()
        store_id = first_store.id if first_store else None

        for item in TEST_USERS:
            user = db.query(models.User).filter(models.User.username == item["username"]).first()

            if user:
                user.real_name = item["real_name"]
                user.role = item["role"]
                user.status = "启用"
                user.password_hash = hash_password("123456")
                user.updated_at = datetime.utcnow()
                if item["role"] in {"店长", "收银员", "库存管理员"}:
                    user.store_id = store_id
            else:
                user = models.User(
                    username=item["username"],
                    password_hash=hash_password("123456"),
                    real_name=item["real_name"],
                    role=item["role"],
                    store_id=store_id if item["role"] in {"店长", "收银员", "库存管理员"} else None,
                    status="启用",
                )
                db.add(user)

        db.commit()
        print("测试账号已创建/更新完成，默认密码都是 123456")
    finally:
        db.close()


if __name__ == "__main__":
    main()

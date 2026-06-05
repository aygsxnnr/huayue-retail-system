from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from sqlalchemy.orm import declarative_base, sessionmaker


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "huayue.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SQLALCHEMY_DATABASE_URL = URL.create("sqlite", database=str(DB_PATH))

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_member_schema() -> None:
    """Add sixth-stage member columns for existing SQLite databases."""
    with engine.begin() as connection:
        existing_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(members)").fetchall()
        }
        column_sql = {
            "total_orders": "ALTER TABLE members ADD COLUMN total_orders INTEGER NOT NULL DEFAULT 0",
            "last_purchase_at": "ALTER TABLE members ADD COLUMN last_purchase_at DATETIME",
            "status": "ALTER TABLE members ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT '正常'",
            "registered_store": "ALTER TABLE members ADD COLUMN registered_store VARCHAR(100) NOT NULL DEFAULT '华悦线上会员中心'",
        }
        for column, sql in column_sql.items():
            if column not in existing_columns:
                try:
                    connection.execute(text(sql))
                except OperationalError as exc:
                    raise RuntimeError(
                        f"旧 SQLite 数据库缺少 members.{column}，且当前数据库不可写。"
                        f"请删除 {DB_PATH} 后重新执行 seed。"
                    ) from exc

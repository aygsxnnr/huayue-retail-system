from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
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
    connect_args={
        "check_same_thread": False,
        "timeout": 60,
    },
    pool_size=30,
    max_overflow=30,
    pool_timeout=60,
    pool_pre_ping=True,
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=60000")
    cursor.close()


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


def ensure_coupon_schema() -> None:
    """Add coupon rule columns for existing SQLite databases."""
    with engine.begin() as connection:
        existing_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(coupons)").fetchall()
        }
        column_sql = {
            "per_member_limit": "ALTER TABLE coupons ADD COLUMN per_member_limit INTEGER",
            "per_order_use_limit": "ALTER TABLE coupons ADD COLUMN per_order_use_limit INTEGER",
            "stackable": "ALTER TABLE coupons ADD COLUMN stackable BOOLEAN NOT NULL DEFAULT 0",
            "total_issue_limit": "ALTER TABLE coupons ADD COLUMN total_issue_limit INTEGER",
            "total_redeem_limit": "ALTER TABLE coupons ADD COLUMN total_redeem_limit INTEGER",
            "applicable_category_ids": "ALTER TABLE coupons ADD COLUMN applicable_category_ids TEXT NOT NULL DEFAULT ''",
            "applicable_product_ids": "ALTER TABLE coupons ADD COLUMN applicable_product_ids TEXT NOT NULL DEFAULT ''",
            "applicable_seasons": "ALTER TABLE coupons ADD COLUMN applicable_seasons TEXT NOT NULL DEFAULT ''",
            "applicable_member_levels": "ALTER TABLE coupons ADD COLUMN applicable_member_levels TEXT NOT NULL DEFAULT ''",
            "applicable_member_groups": "ALTER TABLE coupons ADD COLUMN applicable_member_groups TEXT NOT NULL DEFAULT ''",
            "applicable_store_ids": "ALTER TABLE coupons ADD COLUMN applicable_store_ids TEXT NOT NULL DEFAULT ''",
            "target_tags": "ALTER TABLE coupons ADD COLUMN target_tags TEXT NOT NULL DEFAULT ''",
            "issue_mode": "ALTER TABLE coupons ADD COLUMN issue_mode VARCHAR(30) NOT NULL DEFAULT '手动发放'",
            "auto_issue_enabled": "ALTER TABLE coupons ADD COLUMN auto_issue_enabled BOOLEAN NOT NULL DEFAULT 0",
        }
        for column, sql in column_sql.items():
            if column not in existing_columns:
                try:
                    connection.execute(text(sql))
                except OperationalError as exc:
                    raise RuntimeError(
                        f"旧 SQLite 数据库缺少 coupons.{column}，且当前数据库不可写。"
                        f"请删除 {DB_PATH} 后重新执行 seed。"
                    ) from exc


def ensure_product_schema() -> None:
    """Add product price columns for existing SQLite databases."""
    with engine.begin() as connection:
        existing_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(products)").fetchall()
        }
        column_sql = {
            "sale_price": "ALTER TABLE products ADD COLUMN sale_price FLOAT NOT NULL DEFAULT 0",
            "cost_price": "ALTER TABLE products ADD COLUMN cost_price FLOAT NOT NULL DEFAULT 0",
        }
        for column, sql in column_sql.items():
            if column not in existing_columns:
                try:
                    connection.execute(text(sql))
                except OperationalError as exc:
                    raise RuntimeError(
                        f"旧 SQLite 数据库缺少 products.{column}，且当前数据库不可写。"
                        f"请删除 {DB_PATH} 后重新执行 seed。"
                    ) from exc


def ensure_sales_order_item_schema() -> None:
    """Add order item price snapshot columns for existing SQLite databases."""
    with engine.begin() as connection:
        existing_columns = {
            row[1]
            for row in connection.exec_driver_sql("PRAGMA table_info(sales_order_items)").fetchall()
        }
        column_sql = {
            "unit_cost": "ALTER TABLE sales_order_items ADD COLUMN unit_cost FLOAT NOT NULL DEFAULT 0",
            "cost_amount": "ALTER TABLE sales_order_items ADD COLUMN cost_amount FLOAT NOT NULL DEFAULT 0",
        }
        for column, sql in column_sql.items():
            if column not in existing_columns:
                try:
                    connection.execute(text(sql))
                except OperationalError as exc:
                    raise RuntimeError(
                        f"旧 SQLite 数据库缺少 sales_order_items.{column}，且当前数据库不可写。"
                        f"请删除 {DB_PATH} 后重新执行 seed。"
                    ) from exc

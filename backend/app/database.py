from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
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

# เชื่อมต่อฐานข้อมูล — อ่าน DATABASE_URL จาก environment
# - Docker Compose: postgresql://appuser:apppassword@db:5432/appdb (คอนเทนเนอร์ db)
# - รันในเครื่องโดยไม่ตั้งค่าอะไร: SQLite ไฟล์ backend/astra.db (ข้อมูลไม่หายเมื่อ restart เหมือนกัน)
import os
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

_DEFAULT_SQLITE = Path(__file__).resolve().parents[1] / "astra.db"


def _normalize(url: str) -> str:
    """แปลง URL ให้ใช้ driver psycopg (v3) — Render/Heroku บางที่ให้มาเป็น postgres://"""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _normalize(os.getenv("DATABASE_URL") or f"sqlite:///{_DEFAULT_SQLITE.as_posix()}")
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_pre_ping=True,
)

if IS_SQLITE:
    # SQLite ไม่ตรวจ foreign key ถ้าไม่เปิดเอง — เปิดไว้ให้พฤติกรรมเหมือน PostgreSQL
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_session():
    """Dependency: 1 request = 1 session (FastAPI ปิดให้อัตโนมัติเมื่อจบ request)"""
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """สร้างตารางที่ยังไม่มี แล้ว seed ข้อมูลตั้งต้น (เรียกครั้งเดียวตอนแอปเริ่ม)"""
    from . import models  # noqa: F401 — import เพื่อให้ SQLModel รู้จักทุกตาราง
    from .seed import seed_all

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_all(session)

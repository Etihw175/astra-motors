# เชื่อมต่อฐานข้อมูล — อ่าน DATABASE_URL จาก environment
# - Docker Compose: postgresql://appuser:apppassword@db:5432/appdb (คอนเทนเนอร์ db)
# - รันในเครื่องโดยไม่ตั้งค่าอะไร: SQLite ไฟล์ backend/astra.db (ข้อมูลไม่หายเมื่อ restart เหมือนกัน)
import logging
import os
from pathlib import Path

from sqlalchemy import event, inspect
from sqlmodel import Session, SQLModel, create_engine

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_DEFAULT_SQLITE = _BACKEND_DIR / "astra.db"
# ไฟล์ตั้งค่า alembic อยู่ที่ backend/alembic.ini (ระดับเดียวกันกับไฟล์นี้)
_ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"


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


def _run_migrations() -> bool:
    """รัน `alembic upgrade head` ในโค้ด — คืน True เมื่อ migrate สำเร็จ

    เรียกจาก init_db() ซึ่งทำงานตอน import main.py จึงห้าม raise ออกไป:
    ถ้าหา alembic.ini ไม่เจอ หรือยังไม่ได้ติดตั้งแพ็กเกจ alembic แอปต้องสตาร์ตต่อได้
    โดยเตือนใน log แล้วกลับไปใช้ create_all() เหมือนเดิม
    """
    try:
        from alembic import command
        from alembic.config import Config
    except ModuleNotFoundError:
        logger.warning("ยังไม่ได้ติดตั้ง alembic (pip install -r requirements.txt) — ข้าม migration ไปใช้ create_all() แทน")
        return False

    if not _ALEMBIC_INI.exists():
        logger.warning(
            "หา alembic.ini ไม่เจอที่ %s — ข้าม migration ไปใช้ create_all() แทน "
            "(โครงสร้างที่เปลี่ยนภายหลังจะยังไม่อัปเดต ต้องรัน alembic upgrade head เอง)",
            _ALEMBIC_INI,
        )
        return False

    try:
        config = Config(str(_ALEMBIC_INI))
        # ระบุ script_location เป็น absolute เพราะ cwd ของ uvicorn บน server อาจไม่ใช่ backend/
        config.set_main_option("script_location", str(_BACKEND_DIR / "alembic"))
        command.upgrade(config, "head")
        logger.info("alembic upgrade head สำเร็จ — โครงตารางเป็นรุ่นล่าสุดแล้ว")
        return True
    except Exception as exc:  # noqa: BLE001 — พลาดตอน migrate ห้ามทำให้แอปตายตอนเริ่ม
        logger.warning("รัน migration ไม่สำเร็จ: %s — กลับไปใช้ create_all() แทน", exc)
        return False


def init_db() -> None:
    """เตรียมโครงตาราง แล้ว seed ข้อมูลตั้งต้น (เรียกครั้งเดียวตอนแอปเริ่ม)

    แยก 2 เส้นทางโดยเจตนา:
    - PostgreSQL (production/Render): รัน `alembic upgrade head` ก่อน seed
      เพราะ create_all() เพิ่มได้แค่ตารางใหม่ แก้คอลัมน์/ชนิดของตารางเก่าไม่ได้
      → แก้โมเดลแล้ว deploy งานจะเงียบ ๆ โดยที่โครงจริงไม่เปลี่ยน
    - SQLite (dev ในเครื่อง + pytest): ใช้ create_all() ตามเดิม
      เพราะเทสต์สร้างฐานข้อมูลใหม่ทุกครั้ง ไม่คุ้มค่าที่จะไล่ migration ทีละตัว

    AUTO_MIGRATE=0 = ปิดการ migrate อัตโนมัติ (สำหรับคนที่อยากรันเองก่อน หรือ deploy หลาย instance)
    """
    from . import models  # noqa: F401 — import เพื่อให้ SQLModel รู้จักทุกตาราง
    from .seed import seed_all

    auto_migrate = os.getenv("AUTO_MIGRATE", "1") != "0"

    if IS_SQLITE:
        SQLModel.metadata.create_all(engine)
    elif not auto_migrate:
        logger.warning("AUTO_MIGRATE=0 — ข้าม alembic upgrade head ต้องรัน migration ด้วยมือเอง")
    elif not _run_migrations():
        SQLModel.metadata.create_all(engine)

    if not inspect(engine).has_table("users"):
        # ยังไม่มีโครงสร้าง (เกิดได้เมื่อ AUTO_MIGRATE=0 แล้วยังไม่รัน upgrade) — seed ไม่ได้
        logger.warning("ยังไม่มีตารางในฐานข้อมูล — ข้ามการ seed ให้รัน `alembic upgrade head` ก่อนแล้วเริ่มแอปใหม่")
        return

    with Session(engine) as session:
        seed_all(session)

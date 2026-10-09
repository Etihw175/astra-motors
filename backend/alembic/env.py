"""สคริปต์ที่ Alembic เรียกทุกครั้งที่รัน migration

การต่อสายไฟของไฟล์นี้ (อ่านก่อนแก้):
- ไม่ hardcode URL ฐานข้อมูล — ดึง engine/DATABASE_URL จาก app.database ตัวเดียวกับที่แอปใช้
  ดังนั้น `alembic upgrade head` จะวิ่งไปที่ฐานข้อมูลเดียวกับที่ตั้งใน DATABASE_URL เสมอ
- import app.models ก่อนอ่าน SQLModel.metadata เพราะตารางจะถูกลงทะเบียนตอน import โมดูลนั้น
  (ถ้าลืม import autogenerate จะเห็น metadata ว่างแล้วสั่ง drop ตารางทิ้งทั้งหมด)
- compare_type=True ให้ autogenerate จับการเปลี่ยนชนิดคอลัมน์ได้ ไม่ใช่แค่เพิ่ม/ลบคอลัมน์
- render_as_batch=True เฉพาะ SQLite เพราะ SQLite ไม่มี ALTER COLUMN จริง
  Alembic ต้องใช้วิธี "batch" (สร้างตารางใหม่ + คัดลอกข้อมูล + เปลี่ยนชื่อ) แทน
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlmodel import SQLModel

# ให้ import app.* ได้แม้รัน alembic จากที่อื่น (prepend_sys_path ใน alembic.ini ใช้ได้แค่ตอนรันผ่าน CLI)
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app import models  # noqa: F401,E402 — ต้อง import เพื่อให้ทุกตารางอยู่ใน SQLModel.metadata
from app.database import DATABASE_URL, engine  # noqa: E402

config = context.config

if config.config_file_name is not None:
    # disable_existing_loggers=False: init_db() เรียก alembic ตอนแอปเริ่ม ห้ามไปปิด logger ของ uvicorn
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = SQLModel.metadata


def _is_sqlite(dialect_name: str) -> bool:
    return dialect_name.startswith("sqlite")


def run_migrations_offline() -> None:
    """โหมด offline: ไม่ต่อฐานข้อมูล แค่พิมพ์ SQL ออกมา (ใช้ตอนต้องส่ง SQL ให้ DBA รันเอง)"""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        render_as_batch=_is_sqlite(DATABASE_URL),
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=_is_sqlite(connection.dialect.name),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """โหมด online: ต่อฐานข้อมูลจริงแล้วรัน migration ในทรานแซกชันเดียว

    config.attributes["connection"] คือช่องให้ผู้เรียกส่ง connection ของตัวเองเข้ามาได้
    (tests/test_migrations.py ใช้ช่องนี้ยิง migration ลงไฟล์ SQLite ชั่วคราว ไม่แตะ DATABASE_URL ของแอป)
    ถ้าไม่ส่งมา จะใช้ engine ของแอป (DATABASE_URL) ตามปกติ
    """
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return

    with engine.connect() as conn:
        _run(conn)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

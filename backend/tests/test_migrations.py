"""เทสต์ว่า Alembic migration ใช้งานได้จริง — ขึ้นได้ ลงได้ และมี head เดียว

ทำไมต้องมีเทสต์นี้: ตอน deploy บน PostgreSQL แอปเรียก `alembic upgrade head` ให้อัตโนมัติ
ถ้า migration พัง เว็บจะบูตไม่ขึ้นทั้งระบบ จึงต้องจับให้ได้ตอนรันเทสต์

เทสต์ทั้งไฟล์ยิงลงไฟล์ SQLite ชั่วคราวของตัวเอง (ส่ง connection เข้า env.py ผ่าน
config.attributes) จึงไม่แตะ DATABASE_URL ของแอปและไม่ชนกับเทสต์อื่น
"""
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

from app import models  # noqa: F401 — import เพื่อให้ทุกตารางอยู่ใน SQLModel.metadata

BACKEND_DIR = Path(__file__).resolve().parents[1]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"

# ตารางของ alembic เองไม่ได้อยู่ใน models.py จึงต้องตัดออกก่อนเทียบรายชื่อ
VERSION_TABLE = "alembic_version"


def _base_config() -> Config:
    config = Config(str(ALEMBIC_INI))
    # กำกับ absolute ไว้ เพราะ pytest อาจถูกสั่งรันจาก root ของ repo ไม่ใช่ backend/
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def _config(connection) -> Config:
    config = _base_config()
    config.attributes["connection"] = connection
    return config


@pytest.fixture()
def temp_engine():
    """ฐานข้อมูล SQLite ว่างเปล่าไฟล์ใหม่ทุกครั้ง (ไฟล์จริง ไม่ใช่ :memory: เพราะ alembic เปิดหลาย connection)"""
    tmp = Path(tempfile.mkdtemp(prefix="astra-migration-"))
    engine = create_engine(f"sqlite:///{(tmp / 'migration.db').as_posix()}")
    yield engine
    engine.dispose()


def _table_names(engine) -> set:
    return {name for name in inspect(engine).get_table_names() if name != VERSION_TABLE}


def test_upgrade_head_creates_every_model_table(temp_engine):
    with temp_engine.begin() as connection:
        command.upgrade(_config(connection), "head")

    assert _table_names(temp_engine) == set(SQLModel.metadata.tables)


def test_downgrade_base_drops_every_table(temp_engine):
    with temp_engine.begin() as connection:
        config = _config(connection)
        command.upgrade(config, "head")
        command.downgrade(config, "base")

    assert _table_names(temp_engine) == set()


def test_single_head_no_branching():
    """มี head เดียวเสมอ — ถ้าสองคนสร้าง migration จาก revision เดียวกันจะกลายเป็น 2 head และ upgrade จะพัง"""
    script = ScriptDirectory.from_config(_base_config())
    assert len(script.get_heads()) == 1

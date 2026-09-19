"""ตั้งค่าร่วมของทุกเทสต์: ใช้ฐานข้อมูล SQLite ไฟล์ชั่วคราว แยกจากข้อมูลจริงทุกครั้งที่รัน

ต้องตั้ง DATABASE_URL ก่อน import app (database.py อ่านค่านี้ตอนโหลดโมดูล)
อยากรันเทสต์กับ PostgreSQL ให้ตั้ง TEST_DATABASE_URL เป็นฐานข้อมูลว่างก่อนรัน pytest
"""
import os
import sys
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="astra-test-"))
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL") or f"sqlite:///{(_tmp / 'test.db').as_posix()}"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

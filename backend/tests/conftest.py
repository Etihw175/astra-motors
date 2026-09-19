"""ตั้งค่าร่วมของทุกเทสต์: ใช้ฐานข้อมูล SQLite ไฟล์ชั่วคราว แยกจากข้อมูลจริงทุกครั้งที่รัน

ต้องตั้ง DATABASE_URL ก่อน import app (database.py อ่านค่านี้ตอนโหลดโมดูล)
"""
import os
import sys
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="astra-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

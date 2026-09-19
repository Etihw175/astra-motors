# Event bus ภายในแอป (publish / subscribe)
# service ต้นทางแค่ประกาศว่า "เกิดอะไรขึ้น" เช่น reservation.created โดยไม่ต้องรู้ว่าใครสนใจ
# ส่วน Notification service และ Loyalty service สมัครรับ event แล้วทำงานของตัวเอง
# -> เพิ่ม/ถอด service ปลายทางได้โดยไม่แก้โค้ดต้นทาง (หลักเดียวกับ message broker ใน microservices)
#
# handler ทำงานใน transaction เดียวกับต้นทาง: commit พร้อมกัน ถ้าพังก็ rollback พร้อมกัน
from collections import defaultdict
from typing import Callable

from sqlmodel import Session

_handlers: dict[str, list[Callable]] = defaultdict(list)


def subscribe(event_name: str):
    """decorator: ลงทะเบียนฟังก์ชันให้ทำงานเมื่อมี event ชื่อนี้"""
    def register(handler: Callable) -> Callable:
        _handlers[event_name].append(handler)
        return handler
    return register


def publish(db: Session, event_name: str, **payload) -> None:
    """ส่ง event ไปให้ทุก handler ที่สมัครไว้ (ผู้เรียกเป็นคน commit)"""
    for handler in _handlers[event_name]:
        handler(db, **payload)

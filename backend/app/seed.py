# นำข้อมูลตั้งต้นจาก data.py ลงฐานข้อมูล (เรียกทุกครั้งที่แอปเริ่ม — ทำซ้ำได้ไม่เกิดข้อมูลซ้ำ)
# - แคตตาล็อก (รถ/โชว์รูม/แผนสินเชื่อ): upsert ให้ตรงกับ data.py เสมอ แก้ราคาใน data.py แล้ว restart ก็อัปเดต
# - บัญชีตัวอย่าง: สร้างเฉพาะที่ยังไม่มี (ไม่ทับรหัสผ่านที่ผู้ใช้เปลี่ยนเองภายหลัง)
from sqlmodel import Session

from .data import CARS, FINANCE_PLANS, SEED_USERS, SHOWROOMS
from .models import Car, FinancePlan, Showroom
from .security import build_user, find_by_username


def seed_catalog(db: Session) -> None:
    for car in CARS:
        db.merge(Car(**car, drive_code=car["road"]["drive_code"]))
    for showroom in SHOWROOMS:
        db.merge(Showroom(**showroom))
    for plan in FINANCE_PLANS:
        db.merge(FinancePlan(**plan))
    db.commit()


def seed_users(db: Session) -> None:
    for seed in SEED_USERS:
        if find_by_username(db, seed["username"]):
            continue
        build_user(db, **seed)


def seed_all(db: Session) -> None:
    seed_catalog(db)
    seed_users(db)

# ตัวช่วยอ่านข้อมูลที่หลาย router ใช้ร่วมกัน + แปลง row ของฐานข้อมูลเป็น JSON ที่ frontend ใช้
# (รูปแบบ JSON คงเดิมตั้งแต่ยุค mock data — frontend จึงไม่ต้องแก้ตอนย้ายลงฐานข้อมูล)
import secrets
from datetime import date as date_cls
from datetime import datetime

from fastapi import HTTPException
from sqlmodel import Session, func, select

from .models import (
    Car,
    FinancePlan,
    Loan,
    Reservation,
    Review,
    ServiceAppointment,
    Showroom,
    TestDrive,
    User,
)
from .security import can_touch


def new_code(prefix: str) -> str:
    """รหัสอ้างอิง เช่น ADR-2609-7F3A9C — สุ่มส่วนท้าย เดาเลขใบจองของคนอื่นไม่ได้"""
    return f"{prefix}-{datetime.now():%y%m}-{secrets.token_hex(3).upper()}"


# ---------- แคตตาล็อก ----------

def get_car_or_404(db: Session, car_id: str) -> Car:
    car = db.get(Car, car_id)
    if car is None:
        raise HTTPException(status_code=404, detail="ไม่พบรุ่นรถที่ต้องการ")
    return car


def get_showroom_or_404(db: Session, showroom_id: str) -> Showroom:
    showroom = db.get(Showroom, showroom_id)
    if showroom is None:
        raise HTTPException(status_code=404, detail="ไม่พบโชว์รูม")
    return showroom


def rating_map(db: Session) -> dict[str, dict]:
    """คะแนนรีวิวเฉลี่ยของรถทุกรุ่นในคิวรีเดียว: {car_id: {"avg": 4.5, "count": 12}}"""
    rows = db.exec(
        select(Review.car_id, func.avg(Review.rating), func.count(Review.id)).group_by(Review.car_id)
    ).all()
    return {car_id: {"avg": round(float(avg), 1), "count": count} for car_id, avg, count in rows}


# โปรฯ ที่เหลือไม่เกินกี่วันถือว่า "ใกล้หมด" — ใช้ทั้งหน้ารายการที่สนใจและตัวแจ้งเตือน
PROMO_ENDING_DAYS = 3


def promo_status(car: Car, today: date_cls | None = None) -> dict | None:
    """สถานะโปรโมชั่นของรถ 1 คัน (เหลือกี่วัน / หมดอายุแล้ว) — คืน None ถ้ารุ่นนี้ไม่มีโปรฯ

    อยู่ใน crud.py เพราะใช้ร่วมกัน 2 ที่: หน้ารายการที่สนใจ และตัวสร้างแจ้งเตือนโปรฯ ใกล้หมด
    กติกาเรื่องวันจึงมีที่เดียว ไม่ต้องคอยซิงก์ให้ตรงกัน
    """
    if not car.promotion:
        return None
    expires = date_cls.fromisoformat(car.promotion["expires"])
    days_left = (expires - (today or date_cls.today())).days
    return {
        "title": car.promotion["title"],
        "expires": car.promotion["expires"],
        # หมดอายุแล้วให้เป็น 0 ไม่ใช่ติดลบ — หน้าเว็บจะได้ไม่ต้องเช็คเครื่องหมายเอง
        "days_left": max(days_left, 0),
        "active": days_left >= 0,
        "ending_soon": 0 <= days_left <= PROMO_ENDING_DAYS,
    }


def car_dict(car: Car, ratings: dict | None = None) -> dict:
    """รถ 1 คันในรูป JSON ที่หน้าเว็บใช้

    promotion ยังเป็นก้อนดิบเหมือนเดิม (ไม่ลบทิ้ง รูปร่าง response จึงเข้ากันได้กับของเดิม)
    แต่เพิ่ม promotion_status ที่คิดวันหมดอายุมาให้แล้ว เพราะก้อนดิบมีแต่ title/expires
    หน้าเว็บจึงแยกไม่ออกว่าโปรฯ ยังใช้ได้อยู่ไหม แล้วโชว์โปรฯ ที่หมดอายุไปแล้วเป็นของใหม่
    (รุ่นที่ไม่มีโปรฯ ได้ None ตามเดิมของ promo_status)
    """
    data = car.model_dump()
    data["rating"] = (ratings or {}).get(car.id, {"avg": None, "count": 0})
    data["promotion_status"] = promo_status(car)
    return data


def plan_dict(plan: FinancePlan) -> dict:
    return plan.model_dump()


# ---------- การจอง / คำสั่งซื้อ ----------

def get_owned_reservation(db: Session, code: str, user: User) -> Reservation:
    """ใบจองของคนอื่นตอบ 404 (ไม่ใช่ 403) เพื่อไม่บอกว่ามีรหัสนี้อยู่จริง"""
    record = db.get(Reservation, code)
    if record is None or not can_touch(user, record.user_id):
        raise HTTPException(status_code=404, detail="ไม่พบใบจองรหัสนี้ กรุณาตรวจสอบรหัสอีกครั้ง")
    return record


def testdrive_dict(record: TestDrive, db: Session) -> dict:
    car = db.get(Car, record.car_id)
    showroom = db.get(Showroom, record.showroom_id)
    return {
        "code": record.code,
        "car": {"id": car.id, "name": car.name},
        "showroom": showroom.model_dump(),
        "date": record.date.isoformat(),
        "time": record.time,
        "name": record.name,
        "phone": record.phone,
        "contact_message_only": record.contact_message_only,
        "status": record.status,
        "created_at": record.created_at.isoformat(),
    }


def reservation_dict(record: Reservation) -> dict:
    data = {
        "code": record.code,
        "status": record.status,
        "car": {"id": record.car_id, "name": record.car_name, "base_price": record.base_price},
        "color": record.color,
        "options": record.options,
        "total_price": record.total_price,
        "booking_fee": record.booking_fee,
        "payment_method": record.payment_method,
        "promotion": record.promotion,
        "promotion_expired": record.promotion_expired,
        "price_locked_until": record.price_locked_until.isoformat(),
        "customer": {
            "name": record.customer_name,
            "phone": record.customer_phone,
            "email": record.customer_email,
        },
        "contact_message_only": record.contact_message_only,
        "loan_id": record.loan_id,
        "delivery_date": record.delivery_date.isoformat() if record.delivery_date else None,
        "created_at": record.created_at.isoformat(),
    }
    if record.refund:
        data["refund"] = record.refund
    if record.status == "delivery_scheduled":
        from .data import DELIVERY_DOCUMENTS
        data["delivery_documents"] = DELIVERY_DOCUMENTS
    return data


def loan_dict(record: Loan) -> dict:
    return {
        "id": record.id,
        "reservation_code": record.reservation_code,
        "status": record.status,
        "plan": record.plan,
        "down_payment": record.down_payment,
        "down_pct": record.down_pct,
        "principal": record.principal,
        "term_months": record.term_months,
        "monthly_payment": record.monthly_payment,
        "monthly_income": record.monthly_income,
        "applicant": {
            "name": record.applicant_name,
            "phone": record.applicant_phone,
            "occupation": record.occupation,
        },
        "documents": record.documents,
        "created_at": record.created_at.isoformat(),
        "decided_at": record.decided_at.isoformat() if record.decided_at else None,
        "result": record.result,
    }


def service_dict(record: ServiceAppointment, db: Session) -> dict:
    from .data import SERVICE_TYPES
    car = db.get(Car, record.car_id)
    showroom = db.get(Showroom, record.showroom_id)
    service = next((s for s in SERVICE_TYPES if s["id"] == record.service_type), None)
    return {
        "code": record.code,
        "car": {"id": car.id, "name": car.name},
        "showroom": {"id": showroom.id, "name": showroom.name, "phone": showroom.phone},
        "date": record.date.isoformat(),
        "time": record.time,
        "service_type": service or {"id": record.service_type, "name": record.service_type},
        "mileage_km": record.mileage_km,
        "note": record.note,
        "status": record.status,
        "created_at": record.created_at.isoformat(),
    }

# Router: จองทดลองขับ + จองรถออนไลน์ (journey ขั้นตอน 4, 6, 8)
# ข้อมูลเก็บใน memory ชั่วคราว — restart แล้วหาย (สัปดาห์ที่ 2 จะย้ายลง PostgreSQL)
from datetime import date as date_cls, datetime, timedelta

from fastapi import APIRouter, HTTPException

from ..data import (
    BOOKING_FEE,
    CARS,
    DELIVERY_DOCUMENTS,
    PRICE_LOCK_DAYS,
    REFUND_FULL_WITHIN_DAYS,
    SHOWROOMS,
    TESTDRIVE_HOURS,
)
from ..schemas import DeliveryCreate, ReservationCreate, TestDriveCreate
from .showrooms import _is_slot_taken

router = APIRouter(prefix="/api", tags=["bookings"])

TESTDRIVES: dict[str, dict] = {}
RESERVATIONS: dict[str, dict] = {}
_counter = {"testdrive": 0, "reservation": 0}


def _find_car(car_id: str) -> dict:
    for car in CARS:
        if car["id"] == car_id:
            return car
    raise HTTPException(status_code=404, detail="ไม่พบรุ่นรถที่ต้องการ")


# ---------- จองทดลองขับ (ขั้นตอน 4) ----------

@router.post("/testdrives", status_code=201)
def create_testdrive(body: TestDriveCreate):
    car = _find_car(body.car_id)
    showroom = next((s for s in SHOWROOMS if s["id"] == body.showroom_id), None)
    if not showroom:
        raise HTTPException(status_code=404, detail="ไม่พบโชว์รูม")
    if not body.has_license:
        raise HTTPException(status_code=400, detail="ผู้ทดลองขับต้องมีใบขับขี่")
    if body.time not in TESTDRIVE_HOURS:
        raise HTTPException(status_code=400, detail="ช่วงเวลาไม่ถูกต้อง")
    try:
        requested = date_cls.fromisoformat(body.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง")
    if requested <= date_cls.today():
        raise HTTPException(status_code=400, detail="กรุณาเลือกวันล่วงหน้าอย่างน้อย 1 วัน")
    if _is_slot_taken(body.showroom_id, body.date, body.time):
        raise HTTPException(status_code=409, detail="ช่วงเวลานี้ถูกจองแล้ว กรุณาเลือกเวลาอื่น")

    _counter["testdrive"] += 1
    code = f"TD-{datetime.now():%y%m}-{_counter['testdrive']:04d}"
    record = {
        "code": code,
        "car": {"id": car["id"], "name": car["name"]},
        "showroom": showroom,
        "date": body.date,
        "time": body.time,
        "name": body.name,
        "phone": body.phone,
        "contact_message_only": body.contact_message_only,
        "status": "confirmed",
        "created_at": datetime.now().isoformat(),
    }
    TESTDRIVES[code] = record
    return record


@router.get("/testdrives/{code}")
def get_testdrive(code: str):
    if code not in TESTDRIVES:
        raise HTTPException(status_code=404, detail="ไม่พบการจองทดลองขับ")
    return TESTDRIVES[code]


# ---------- จองรถออนไลน์ (ขั้นตอน 6) ----------

@router.post("/reservations", status_code=201)
def create_reservation(body: ReservationCreate):
    car = _find_car(body.car_id)
    color = next((c for c in car["colors"] if c["id"] == body.color_id), None)
    if not color:
        raise HTTPException(status_code=404, detail="ไม่พบสีที่เลือก")
    if body.payment_method not in ("promptpay", "card"):
        raise HTTPException(status_code=400, detail="ช่องทางชำระเงินไม่ถูกต้อง")

    options = [o for o in car["options"] if o["id"] in body.option_ids]
    total = car["price"] + color["extra"] + sum(o["price"] for o in options)

    # ล็อกราคา/โปรโมชั่น ณ วันที่ออกใบจอง (edge case: ราคา/โปรฯ เปลี่ยนภายหลังไม่กระทบใบจองนี้)
    now = datetime.now()
    lock_until = (now + timedelta(days=PRICE_LOCK_DAYS)).date().isoformat()
    promo = car.get("promotion")
    promo_active = bool(promo) and date_cls.fromisoformat(promo["expires"]) >= now.date()

    _counter["reservation"] += 1
    code = f"ADR-{now:%y%m}-{_counter['reservation']:04d}"
    record = {
        "code": code,
        "status": "reserved",  # reserved -> delivery_scheduled | cancelled
        "car": {"id": car["id"], "name": car["name"], "base_price": car["price"]},
        "color": color,
        "options": options,
        "total_price": total,
        "booking_fee": BOOKING_FEE,
        "payment_method": body.payment_method,
        "promotion": promo if promo_active else None,
        "promotion_expired": bool(promo) and not promo_active,
        "price_locked_until": lock_until,
        "customer": {"name": body.name, "phone": body.phone, "email": body.email},
        "contact_message_only": body.contact_message_only,
        "loan_id": None,
        "delivery_date": None,
        "created_at": now.isoformat(),
    }
    RESERVATIONS[code] = record
    return record


@router.get("/reservations/{code}")
def get_reservation(code: str):
    if code not in RESERVATIONS:
        raise HTTPException(status_code=404, detail="ไม่พบใบจองรหัสนี้ กรุณาตรวจสอบรหัสอีกครั้ง")
    return RESERVATIONS[code]


@router.post("/reservations/{code}/cancel")
def cancel_reservation(code: str):
    """ยกเลิกใบจอง (edge case) — เงินจองคืนเต็มจำนวนถ้ายกเลิกภายในกำหนด"""
    record = RESERVATIONS.get(code)
    if not record:
        raise HTTPException(status_code=404, detail="ไม่พบใบจองรหัสนี้")
    if record["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="ใบจองนี้ถูกยกเลิกไปแล้ว")

    created = datetime.fromisoformat(record["created_at"])
    within_full_refund = (datetime.now() - created).days < REFUND_FULL_WITHIN_DAYS
    record["status"] = "cancelled"
    record["refund"] = {
        "amount": BOOKING_FEE if within_full_refund else int(BOOKING_FEE * 0.5),
        "full_refund": within_full_refund,
        "note": (
            "ได้รับเงินจองคืนเต็มจำนวนภายใน 5-7 วันทำการ"
            if within_full_refund
            else f"ยกเลิกหลัง {REFUND_FULL_WITHIN_DAYS} วัน ได้รับคืน 50% ตามเงื่อนไขใบจอง"
        ),
    }
    return record


@router.post("/reservations/{code}/delivery")
def schedule_delivery(code: str, body: DeliveryCreate):
    """นัดรับรถหลังสินเชื่ออนุมัติ (ขั้นตอน 8) — คืนรายการเอกสารที่ต้องเตรียม"""
    record = RESERVATIONS.get(code)
    if not record:
        raise HTTPException(status_code=404, detail="ไม่พบใบจองรหัสนี้")
    if record["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="ใบจองนี้ถูกยกเลิกแล้ว ไม่สามารถนัดรับรถได้")
    try:
        requested = date_cls.fromisoformat(body.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง")
    if requested <= date_cls.today():
        raise HTTPException(status_code=400, detail="กรุณาเลือกวันล่วงหน้าอย่างน้อย 1 วัน")

    record["delivery_date"] = body.date
    record["status"] = "delivery_scheduled"
    record["delivery_documents"] = DELIVERY_DOCUMENTS
    return record

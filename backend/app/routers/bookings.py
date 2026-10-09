# Router: จองทดลองขับ + จองรถออนไลน์ + นัดรับรถ (journey ขั้นตอน 4, 5)
# - จองทดลองขับ: guest จองได้ ถ้าล็อกอินอยู่จะผูกเข้าบัญชี (ดูใน "การจองของฉัน" + ได้คะแนน)
# - จองซื้อรถ: ต้องล็อกอิน (มีการชำระเงินและข้อมูลส่วนตัว) และเจ้าของ/ผู้ดูแลเท่านั้นที่ดู/แก้ได้
from datetime import date as date_cls, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..crud import (
    get_car_or_404,
    get_owned_reservation,
    get_showroom_or_404,
    loan_dict,
    new_code,
    reservation_dict,
    service_dict,
    testdrive_dict,
)
from ..data import BOOKING_FEE, PRICE_LOCK_DAYS, REFUND_FULL_WITHIN_DAYS, TESTDRIVE_HOURS
from ..database import get_session
from ..events import publish
from ..models import Loan, Reservation, ServiceAppointment, TestDrive, User
from ..schemas import DeliveryCreate, ReservationCreate, TestDriveCreate
from ..security import can_touch, get_current_user, get_optional_user, require_admin
from .loans import settle_due_loans
from .showrooms import is_slot_taken, parse_future_date

router = APIRouter(prefix="/api", tags=["bookings"])


# ---------- จองทดลองขับ (ขั้นตอน 4) ----------

def _get_testdrive(db: Session, code: str, user: User | None) -> TestDrive:
    record = db.get(TestDrive, code)
    if record is None:
        raise HTTPException(status_code=404, detail="ไม่พบการจองทดลองขับ")
    # การจองที่ผูกบัญชีแล้ว ดูได้เฉพาะเจ้าของ/ผู้ดูแล — การจองแบบ guest ใช้รหัสจอง (สุ่ม เดาไม่ได้) แทนรหัสผ่าน
    if record.user_id is not None and (user is None or not can_touch(user, record.user_id)):
        raise HTTPException(status_code=404, detail="ไม่พบการจองทดลองขับ")
    return record


@router.post("/testdrives", status_code=201)
def create_testdrive(
    body: TestDriveCreate,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_session),
):
    car = get_car_or_404(db, body.car_id)
    get_showroom_or_404(db, body.showroom_id)
    if not body.has_license:
        raise HTTPException(status_code=400, detail="ผู้ทดลองขับต้องมีใบขับขี่")
    if body.time not in TESTDRIVE_HOURS:
        raise HTTPException(status_code=400, detail="ช่วงเวลาไม่ถูกต้อง")
    day = parse_future_date(body.date)
    if is_slot_taken(db, body.showroom_id, day, body.time):
        raise HTTPException(status_code=409, detail="ช่วงเวลานี้ถูกจองแล้ว กรุณาเลือกเวลาอื่น")

    record = TestDrive(
        code=new_code("TD"),
        user_id=user.id if user else None,
        car_id=car.id,
        showroom_id=body.showroom_id,
        date=day,
        time=body.time,
        name=body.name.strip(),
        phone=body.phone.strip(),
        contact_message_only=body.contact_message_only,
    )
    db.add(record)
    publish(db, "testdrive.booked", record=record, car=car)
    db.commit()
    db.refresh(record)
    return testdrive_dict(record, db)


@router.get("/testdrives/{code}")
def get_testdrive(
    code: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_session),
):
    return testdrive_dict(_get_testdrive(db, code, user), db)


@router.post("/testdrives/{code}/cancel")
def cancel_testdrive(
    code: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_session),
):
    """ยกเลิกนัดทดลองขับ — คิวเวลานั้นกลับมาว่างให้ลูกค้าคนอื่นทันที"""
    record = _get_testdrive(db, code, user)
    if record.status == "cancelled":
        raise HTTPException(status_code=400, detail="นัดทดลองขับนี้ถูกยกเลิกไปแล้ว")
    if record.date <= date_cls.today():
        raise HTTPException(status_code=400, detail="ยกเลิกได้ก่อนวันนัดอย่างน้อย 1 วัน กรุณาติดต่อโชว์รูม")
    record.status = "cancelled"
    db.add(record)
    publish(db, "testdrive.cancelled", record=record)
    db.commit()
    db.refresh(record)
    return testdrive_dict(record, db)


# ---------- จองรถออนไลน์ (ขั้นตอน 5) ----------
# ตรรกะ "คิดราคา" และ "ออกใบจอง" ถูกแยกเป็นฟังก์ชันด้านล่าง เพราะมี 2 เส้นทางที่ใช้ร่วมกัน:
#   1) POST /api/reservations (legacy) — ออกใบจองทันที สมมติว่าจ่ายเงินจองแล้ว
#   2) Payment service (routers/payments.py) — เส้นทางที่หน้าเว็บใช้จริง: จ่ายก่อน แล้วค่อยออกใบจอง
# ห้าม copy-paste ตรรกะนี้ไปที่อื่น ไม่งั้นราคา/การล็อกโปรฯ ของสองเส้นทางจะเพี้ยนไม่ตรงกัน


def quote_reservation(db: Session, car_id: str, color_id: str, option_ids: list[str]) -> dict:
    """คิดราคาสเปคที่เลือก + สถานะโปรโมชั่น ณ วันนี้ (ไม่เขียนฐานข้อมูล)"""
    car = get_car_or_404(db, car_id)
    color = next((c for c in car.colors if c["id"] == color_id), None)
    if not color:
        raise HTTPException(status_code=404, detail="ไม่พบสีที่เลือก")

    # ออปชันที่ไม่มีในรุ่นนี้ต้องตอบ 400 ไม่ใช่เงียบ ๆ ตัดทิ้ง
    # ของเดิมกรองด้วย list comprehension เฉย ๆ ลูกค้าที่พิมพ์ id ผิด (หรือหน้าเว็บส่ง id เก่า
    # หลังแคตตาล็อกเปลี่ยน) จึงได้ใบจองราคาฐานทั้งที่เห็นยอดรวมอีกราคาบนหน้าจอ
    known = {o["id"]: o for o in car.options}
    unknown = [oid for oid in dict.fromkeys(option_ids) if oid not in known]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"ไม่พบออปชันรหัส {', '.join(unknown)} ในรุ่น {car.name}",
        )
    options = [o for o in car.options if o["id"] in option_ids]
    total = car.price + color["extra"] + sum(o["price"] for o in options)

    # ล็อกราคา/โปรโมชั่น ณ วันที่ออกใบจอง (edge case: ราคา/โปรฯ เปลี่ยนภายหลังไม่กระทบใบจองนี้)
    promo = car.promotion
    promo_active = bool(promo) and date_cls.fromisoformat(promo["expires"]) >= date_cls.today()
    return {
        "car": car,
        "color": color,
        "options": options,
        "total_price": total,
        "booking_fee": BOOKING_FEE,
        "promotion": promo if promo_active else None,
        "promotion_expired": bool(promo) and not promo_active,
    }


def issue_reservation(db: Session, user: User, quote: dict, *, payment_method: str,
                      name: str, phone: str, email: str,
                      contact_message_only: bool = False) -> Reservation:
    """ออกใบจองอิเล็กทรอนิกส์ + ประกาศ event (ผู้เรียกเป็นคน commit เหมือน publish ตัวอื่น)"""
    car = quote["car"]
    record = Reservation(
        code=new_code("ADR"),
        user_id=user.id,
        car_id=car.id,
        car_name=car.name,
        base_price=car.price,
        color=quote["color"],
        options=quote["options"],
        total_price=quote["total_price"],
        booking_fee=quote["booking_fee"],
        payment_method=payment_method,
        promotion=quote["promotion"],
        promotion_expired=quote["promotion_expired"],
        price_locked_until=date_cls.today() + timedelta(days=PRICE_LOCK_DAYS),
        customer_name=name.strip(),
        customer_phone=phone.strip(),
        customer_email=email.strip(),
        contact_message_only=contact_message_only,
    )
    db.add(record)
    publish(db, "reservation.created", record=record)
    return record


@router.post("/reservations", status_code=201)
def create_reservation(
    body: ReservationCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_session),
):
    """ออกใบจองทันทีโดยไม่ผ่านการชำระเงิน — เฉพาะผู้ดูแลระบบ/พนักงานโชว์รูม

    ลูกค้าต้องเดินเส้นทางจริงคือ Payment service (POST /api/payments → /confirm)
    คือจ่ายเงินจองให้สำเร็จก่อน แล้วระบบจึงออกใบจองให้ในทรานแซกชันเดียวกัน

    ทำไมต้องปิดไม่ให้ลูกค้าเรียก: เส้นนี้ออกใบจองโดยไม่มีเงินเข้า และใบจองแต่ละใบให้คะแนนสะสม
    ลูกค้าที่ล็อกอินอยู่จึงยิงซ้ำ ๆ เพื่อปั๊มคะแนนแลกของรางวัลได้ฟรี (loyalty farming)
    ที่คงไว้เพราะมีการใช้งานจริง: พนักงานรับจองให้ลูกค้า walk-in ที่จ่ายเงินสดหน้าเคาน์เตอร์
    """
    if body.payment_method not in ("promptpay", "card"):
        raise HTTPException(status_code=400, detail="ช่องทางชำระเงินไม่ถูกต้อง")

    quote = quote_reservation(db, body.car_id, body.color_id, body.option_ids)
    record = issue_reservation(
        db, admin, quote,
        payment_method=body.payment_method,
        name=body.name, phone=body.phone, email=body.email,
        contact_message_only=body.contact_message_only,
    )
    db.commit()
    db.refresh(record)
    return reservation_dict(record)


@router.get("/reservations/{code}")
def get_reservation(
    code: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    return reservation_dict(get_owned_reservation(db, code, user))


@router.post("/reservations/{code}/cancel")
def cancel_reservation(
    code: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """ยกเลิกใบจอง (edge case) — เงินจองคืนเต็มจำนวนถ้ายกเลิกภายในกำหนด"""
    record = get_owned_reservation(db, code, user)
    if record.status == "cancelled":
        raise HTTPException(status_code=400, detail="ใบจองนี้ถูกยกเลิกไปแล้ว")
    if record.status == "delivery_scheduled":
        raise HTTPException(status_code=400, detail="นัดรับรถแล้ว ยกเลิกออนไลน์ไม่ได้ กรุณาติดต่อโชว์รูม")

    # ยกเลิกคำขอสินเชื่อที่ผูกกับใบจองนี้ไปด้วย
    # เลือก "ยกเลิกตามไป" ไม่ใช่ "ห้ามยกเลิกถ้าสินเชื่อผ่านแล้ว" เพราะลูกค้ามีสิทธิ์ถอนการจอง
    # ตามเงื่อนไขคืนเงินเสมอ การบังคับให้ค้างไว้เพราะไฟแนนซ์อนุมัติแล้วไม่ยุติธรรมกับลูกค้า
    # ถ้าไม่ยกเลิก: settle_due_loans จะเดินต่อแล้วส่งแจ้งเตือน "สินเชื่ออนุมัติแล้ว"
    # ของใบจองที่ยกเลิกไปแล้ว และ record ค้างสถานะ approved ให้หลังบ้านสับสน
    if record.loan_id:
        loan = db.get(Loan, record.loan_id)
        if loan and loan.status in ("reviewing", "approved"):
            loan.status = "cancelled"
            loan.decided_at = datetime.now()
            loan.result = {"message": f"คำขอสินเชื่อถูกยกเลิกพร้อมใบจอง {record.code}"}
            db.add(loan)

    within_full_refund = (datetime.now() - record.created_at).days < REFUND_FULL_WITHIN_DAYS
    record.status = "cancelled"
    record.refund = {
        "amount": record.booking_fee if within_full_refund else int(record.booking_fee * 0.5),
        "full_refund": within_full_refund,
        "note": (
            "ได้รับเงินจองคืนเต็มจำนวนภายใน 5-7 วันทำการ"
            if within_full_refund
            else f"ยกเลิกหลัง {REFUND_FULL_WITHIN_DAYS} วัน ได้รับคืน 50% ตามเงื่อนไขใบจอง"
        ),
    }
    db.add(record)
    publish(db, "reservation.cancelled", record=record)
    db.commit()
    db.refresh(record)
    return reservation_dict(record)


@router.post("/reservations/{code}/delivery")
def schedule_delivery(
    code: str,
    body: DeliveryCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """นัดรับรถ — ต้องมีสินเชื่อที่อนุมัติแล้ว (หรือไม่ได้ยื่นสินเชื่อ = ซื้อเงินสด)"""
    record = get_owned_reservation(db, code, user)
    if record.status == "cancelled":
        raise HTTPException(status_code=400, detail="ใบจองนี้ถูกยกเลิกแล้ว ไม่สามารถนัดรับรถได้")
    if record.loan_id:
        settle_due_loans(db)
        loan = db.get(Loan, record.loan_id)
        if loan and loan.status != "approved":
            raise HTTPException(status_code=400, detail="ต้องรอสินเชื่ออนุมัติก่อน จึงจะนัดวันรับรถได้")
    day = parse_future_date(body.date)

    record.delivery_date = day
    record.status = "delivery_scheduled"
    db.add(record)
    publish(db, "delivery.scheduled", record=record)
    db.commit()
    db.refresh(record)
    return reservation_dict(record)


# ---------- ภาพรวมการจองทั้งหมดของฉัน (ขั้นตอน 6 ติดตามสถานะ) ----------

@router.get("/me/bookings", tags=["users"], summary="การจองทั้งหมดของฉัน")
def my_bookings(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    """รวมทุกอย่างที่ผูกกับบัญชีไว้ในที่เดียว: ทดลองขับ, ใบจอง (+ สถานะสินเชื่อ), นัดเข้าศูนย์"""
    settle_due_loans(db)
    testdrives = db.exec(
        select(TestDrive).where(TestDrive.user_id == user.id).order_by(TestDrive.created_at.desc())
    ).all()
    reservations = db.exec(
        select(Reservation).where(Reservation.user_id == user.id).order_by(Reservation.created_at.desc())
    ).all()
    services = db.exec(
        select(ServiceAppointment)
        .where(ServiceAppointment.user_id == user.id)
        .order_by(ServiceAppointment.created_at.desc())
    ).all()

    items = []
    for r in reservations:
        data = reservation_dict(r)
        loan = db.get(Loan, r.loan_id) if r.loan_id else None
        data["loan"] = loan_dict(loan) if loan else None
        items.append(data)

    return {
        "testdrives": [testdrive_dict(t, db) for t in testdrives],
        "reservations": items,
        "service_appointments": [service_dict(s, db) for s in services],
    }

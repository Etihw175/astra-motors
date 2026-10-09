# Payment service — การชำระเงินจองแบบจำลองที่เดินตามขั้นตอนของจริง (journey ขั้นตอน 5)
#
# ทำไมต้องมี service นี้: เส้นทางเดิม (POST /api/reservations) ออกใบจองทันทีโดยสมมติว่าเงินเข้าแล้ว
# ซึ่งไม่ตรงกับความจริง — ของจริงต้องสร้าง "payment intent" ก่อน แล้วรอผลจากธนาคาร/บัตร
# แล้วจึงออกใบจอง ลำดับนี้สำคัญเพราะถ้าเงินไม่เข้าหรือลูกค้าปิดหน้าไปกลางทาง
# ต้องไม่มีใบจองค้างอยู่ในระบบ (และไม่มีคะแนน/แจ้งเตือนหลุดออกไป)
#
# ขั้นตอน: POST /api/payments (pending + QR) → ลูกค้าจ่าย → POST /{id}/confirm (paid + ออกใบจอง)
#
# ของจริง "confirm" มาจาก webhook ของ payment gateway ไม่ใช่จากเบราว์เซอร์ของลูกค้า
# ในโปรเจกต์นี้เปิดเป็น endpoint ให้กดจำลองได้ เพื่อเดโมให้ครบวงจรโดยไม่ต้องต่อธนาคารจริง
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..crud import new_code
from ..data import PAYMENT_EXPIRE_MINUTES, SHOP_PROMPTPAY_NAME, SHOP_PROMPTPAY_PHONE
from ..database import get_session
from ..events import publish
from ..models import Payment, User
from ..promptpay import promptpay_payload, qr_svg
from ..schemas import PaymentCreate
from ..security import can_touch, get_current_user
from .bookings import issue_reservation, quote_reservation

router = APIRouter(prefix="/api/payments", tags=["payments"])

METHODS = ("promptpay", "card")

# ข้อความเตือนที่ต้องโผล่ทุกที่ที่มีการชำระเงิน — ห้ามเอาออกแม้หน้าเว็บจะมีป้ายของตัวเองแล้ว
SIMULATION_NOTE = (
    "ระบบชำระเงินนี้เป็นการจำลองสำหรับโปรเจกต์การศึกษา "
    "QR ถูกสร้างตามสเปก EMVCo จริงแต่ปลายทางเป็นบัญชีสมมติ ห้ามสแกนจ่ายเงินจริง"
)


def _expire_if_due(db: Session, record: Payment) -> Payment:
    """เลยเวลาแล้วยัง pending = หมดอายุ — เช็คตอนอ่าน ไม่ต้องมี cron คอยกวาด

    ของจริง gateway จะยกเลิกรายการให้เองเมื่อหมดอายุ ที่นี่จึงตัดสินจาก expires_at ตอนมีคนถาม
    """
    if record.status == "pending" and record.expires_at < datetime.now():
        record.status = "expired"
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def _get_owned_payment(db: Session, payment_id: str, user: User) -> Payment:
    """รายการของคนอื่นตอบ 404 (ไม่ใช่ 403) เพื่อไม่บอกว่ามีรหัสนี้อยู่จริง"""
    record = db.get(Payment, payment_id)
    if record is None or not can_touch(user, record.user_id):
        raise HTTPException(status_code=404, detail="ไม่พบรายการชำระเงินนี้")
    return record


def payment_dict(record: Payment, *, with_qr: bool = False) -> dict:
    data = {
        "id": record.id,
        "purpose": record.purpose,
        "amount": record.amount,
        "method": record.method,
        "status": record.status,
        "car": {"id": record.reference.get("car_id"), "name": record.reference.get("car_name")},
        "total_price": record.reference.get("total_price"),
        "card_last4": record.reference.get("card_last4"),
        "expires_at": record.expires_at.isoformat(),
        "expires_in": max(0, int((record.expires_at - datetime.now()).total_seconds())),
        "paid_at": record.paid_at.isoformat() if record.paid_at else None,
        "reservation_code": record.reservation_code,
        "created_at": record.created_at.isoformat(),
        # ผู้รับเงินเป็นบัญชีสมมติ — ทุก response ต้องกำกับไว้ให้หน้าเว็บเอาไปแสดงเป็นป้ายเตือน
        "simulation": True,
        "simulation_note": SIMULATION_NOTE,
    }
    if record.method == "promptpay":
        data["promptpay"] = {"name": SHOP_PROMPTPAY_NAME, "phone": SHOP_PROMPTPAY_PHONE}
        if with_qr and record.qr_payload:
            # ส่ง SVG สด ๆ ใน response — ฐานข้อมูลเก็บแค่ payload จะสร้างรูปใหม่เมื่อไรก็ได้
            data["qr_payload"] = record.qr_payload
            data["qr_svg"] = qr_svg(record.qr_payload)
    return data


@router.post("", status_code=201, summary="เริ่มรายการชำระเงินจอง (payment intent)")
def create_payment(
    body: PaymentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    if body.method not in METHODS:
        raise HTTPException(status_code=400, detail="ช่องทางชำระเงินไม่ถูกต้อง")
    if body.card_last4 is not None and not body.card_last4.isdigit():
        raise HTTPException(status_code=400, detail="เลข 4 ตัวท้ายบัตรต้องเป็นตัวเลขเท่านั้น")

    quote = quote_reservation(db, body.car_id, body.color_id, body.option_ids)
    car = quote["car"]
    amount = quote["booking_fee"]

    record = Payment(
        id=new_code("PAY"),
        user_id=user.id,
        purpose="booking_fee",
        amount=amount,
        method=body.method,
        status="pending",
        # snapshot ของสเปค + ผู้จอง: ใบจองตอน confirm ต้องใช้ราคาเดียวกับที่ลูกค้าเห็นตอนกดจ่าย
        reference={
            "car_id": car.id,
            "car_name": car.name,
            "color_id": quote["color"]["id"],
            "option_ids": [o["id"] for o in quote["options"]],
            "total_price": quote["total_price"],
            "name": body.name.strip(),
            "phone": body.phone.strip(),
            "email": body.email.strip(),
            "contact_message_only": body.contact_message_only,
            "card_last4": body.card_last4,
        },
        expires_at=datetime.now().replace(microsecond=0) + timedelta(minutes=PAYMENT_EXPIRE_MINUTES),
    )
    if body.method == "promptpay":
        record.qr_payload = promptpay_payload(SHOP_PROMPTPAY_PHONE, amount)

    db.add(record)
    db.commit()
    db.refresh(record)
    return payment_dict(record, with_qr=True)


@router.get("/{payment_id}", summary="สถานะรายการชำระเงิน (เจ้าของ/ผู้ดูแลเท่านั้น)")
def get_payment(
    payment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """หน้าเว็บ poll endpoint นี้ทุก 3 วินาที — ในระบบจริงใช้ webhook จาก gateway แทนการ poll"""
    record = _expire_if_due(db, _get_owned_payment(db, payment_id, user))
    return payment_dict(record, with_qr=True)


@router.post("/{payment_id}/confirm", summary="จำลองว่าธนาคาร/บัตรยืนยันการชำระเงินแล้ว")
def confirm_payment(
    payment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """pending → paid แล้วออกใบจองจริงในทรานแซกชันเดียวกัน

    ออกใบจองที่นี่ที่เดียวพร้อมกับการเปลี่ยนสถานะ เพื่อไม่ให้เกิดสถานะ "จ่ายแล้วแต่ไม่มีใบจอง"
    เมื่อระหว่างนั้นเกิดข้อผิดพลาด (ถ้าพัง rollback พร้อมกันทั้งก้อน)
    """
    record = _expire_if_due(db, _get_owned_payment(db, payment_id, user))
    if record.status == "paid":
        raise HTTPException(status_code=409, detail="รายการนี้ชำระเงินเรียบร้อยแล้ว ไม่ต้องยืนยันซ้ำ")
    if record.status == "expired":
        raise HTTPException(status_code=400,
                            detail="QR/รายการชำระเงินหมดอายุแล้ว กรุณาเริ่มรายการชำระเงินใหม่")
    if record.status != "pending":
        raise HTTPException(status_code=400, detail="รายการนี้ถูกยกเลิกแล้ว กรุณาเริ่มรายการชำระเงินใหม่")

    ref = record.reference
    quote = quote_reservation(db, ref["car_id"], ref["color_id"], ref.get("option_ids", []))
    reservation = issue_reservation(
        db, user, quote,
        payment_method=record.method,
        name=ref["name"], phone=ref["phone"], email=ref["email"],
        contact_message_only=ref.get("contact_message_only", False),
    )
    # ต้อง flush ก่อน เพราะ payments.reservation_code เป็น FK ไปที่ reservations.code
    db.flush()

    record.status = "paid"
    record.paid_at = datetime.now().replace(microsecond=0)
    record.reservation_code = reservation.code
    db.add(record)
    publish(db, "payment.paid", payment=record, reservation=reservation)
    db.commit()
    db.refresh(record)
    return payment_dict(record)


@router.post("/{payment_id}/cancel", summary="ยกเลิกรายการชำระเงินที่ยังไม่จ่าย")
def cancel_payment(
    payment_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    record = _expire_if_due(db, _get_owned_payment(db, payment_id, user))
    if record.status == "paid":
        raise HTTPException(status_code=400, detail="ชำระเงินแล้ว ยกเลิกรายการชำระเงินไม่ได้ "
                                                   "ให้ยกเลิกที่ใบจองเพื่อขอคืนเงินจองแทน")
    if record.status != "pending":
        raise HTTPException(status_code=400, detail="รายการนี้ปิดไปแล้ว")
    record.status = "failed"
    db.add(record)
    db.commit()
    db.refresh(record)
    return payment_dict(record)

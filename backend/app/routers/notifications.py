# Router + Notification service (journey ขั้นตอน 6: แจ้งเตือนความคืบหน้า ไม่ต้องโทรถามโชว์รูม)
# service นี้ไม่ถูกเรียกตรง ๆ จาก router อื่น — สมัครรับ event จาก events.py แล้วสร้างแจ้งเตือนเอง
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select, update

from ..database import get_session
from ..events import subscribe
from ..models import Notification, User
from ..security import get_current_user
from .loans import settle_due_loans

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

STATUS_PAGE = "/pages/status.html"
AFTER_SALES_PAGE = "/pages/after-sales.html"


def notify(db: Session, user_id: int | None, kind: str, title: str, message: str,
           link: str | None = None) -> None:
    """เพิ่มแจ้งเตือนลงกล่องของผู้ใช้ (guest ไม่มีกล่องแจ้งเตือน จึงข้าม)"""
    if user_id is None:
        return
    db.add(Notification(user_id=user_id, kind=kind, title=title, message=message, link=link))


def _thai_date(day) -> str:
    return day.strftime("%d/%m/") + str(day.year + 543)


# ---------- event handlers ----------

@subscribe("testdrive.booked")
def _on_testdrive_booked(db, record, car, **_):
    notify(db, record.user_id, "testdrive.booked", "ยืนยันนัดทดลองขับแล้ว",
           f"{car.name} วันที่ {_thai_date(record.date)} เวลา {record.time} น. "
           f"(รหัส {record.code}) กรุณานำใบขับขี่ตัวจริงมาด้วย", STATUS_PAGE)


@subscribe("testdrive.cancelled")
def _on_testdrive_cancelled(db, record, **_):
    notify(db, record.user_id, "testdrive.cancelled", "ยกเลิกนัดทดลองขับแล้ว",
           f"นัดรหัส {record.code} ถูกยกเลิก คิวเวลานี้เปิดให้ลูกค้าท่านอื่นจองต่อได้", STATUS_PAGE)


@subscribe("reservation.created")
def _on_reservation_created(db, record, **_):
    notify(db, record.user_id, "reservation.created", "ออกใบจองอิเล็กทรอนิกส์แล้ว",
           f"{record.car_name} ราคารวม {record.total_price:,} บาท ล็อกราคาถึง "
           f"{_thai_date(record.price_locked_until)} (รหัส {record.code})",
           f"{STATUS_PAGE}?code={record.code}")


@subscribe("reservation.cancelled")
def _on_reservation_cancelled(db, record, **_):
    refund = record.refund or {}
    notify(db, record.user_id, "reservation.cancelled", "ยกเลิกใบจองแล้ว",
           f"ใบจอง {record.code} ถูกยกเลิก เงินคืน {refund.get('amount', 0):,} บาท — {refund.get('note', '')}",
           f"{STATUS_PAGE}?code={record.code}")


@subscribe("loan.submitted")
def _on_loan_submitted(db, record, **_):
    notify(db, record.user_id, "loan.submitted", "ได้รับคำขอสินเชื่อแล้ว",
           f"{record.plan['name']} ค่างวดประมาณ {record.monthly_payment:,} บาท/เดือน "
           f"กำลังพิจารณา ระบบจะแจ้งผลทันทีที่ทราบ",
           f"{STATUS_PAGE}?code={record.reservation_code}")


@subscribe("loan.decided")
def _on_loan_decided(db, record, **_):
    if record.status == "approved":
        title = "สินเชื่อได้รับการอนุมัติ"
        message = "เลือกวันนัดรับรถได้เลยที่หน้าการจองของฉัน"
    else:
        title = "สินเชื่อไม่ผ่านการอนุมัติ"
        message = "ระบบคำนวณทางเลือกให้แล้ว เช่น เพิ่มเงินดาวน์หรือยืดระยะผ่อน"
    notify(db, record.user_id, "loan.decided", title, message,
           f"{STATUS_PAGE}?code={record.reservation_code}")


@subscribe("delivery.scheduled")
def _on_delivery_scheduled(db, record, **_):
    notify(db, record.user_id, "delivery.scheduled", "นัดรับรถเรียบร้อย",
           f"{record.car_name} วันที่ {_thai_date(record.delivery_date)} "
           f"อย่าลืมเตรียมเอกสารตามรายการในหน้าการจอง", f"{STATUS_PAGE}?code={record.code}")


@subscribe("service.booked")
def _on_service_booked(db, record, **_):
    notify(db, record.user_id, "service.booked", "ยืนยันนัดเข้าศูนย์บริการแล้ว",
           f"วันที่ {_thai_date(record.date)} เวลา {record.time} น. (รหัส {record.code})",
           AFTER_SALES_PAGE)


@subscribe("service.cancelled")
def _on_service_cancelled(db, record, **_):
    notify(db, record.user_id, "service.cancelled", "ยกเลิกนัดเข้าศูนย์บริการแล้ว",
           f"นัดรหัส {record.code} ถูกยกเลิก", AFTER_SALES_PAGE)


@subscribe("points.redeemed")
def _on_points_redeemed(db, user_id, reward, voucher, **_):
    notify(db, user_id, "points.redeemed", "แลกของรางวัลสำเร็จ",
           f"{reward['name']} (ใช้ {reward['points']:,} คะแนน) รหัสสิทธิ์ {voucher} "
           f"แสดงรหัสนี้ที่ศูนย์บริการเพื่อรับสิทธิ์",
           AFTER_SALES_PAGE)


# ---------- endpoints ----------

@router.get("", summary="แจ้งเตือนของฉัน (ใหม่สุดก่อน)")
def list_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    settle_due_loans(db)   # ผลสินเชื่อที่ครบเวลาแล้วจะกลายเป็นแจ้งเตือนทันที
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)  # noqa: E712
    rows = db.exec(stmt.order_by(Notification.id.desc()).limit(limit)).all()
    return {"items": rows, "unread": _unread_count(db, user.id)}


def _unread_count(db: Session, user_id: int) -> int:
    return db.exec(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id, Notification.is_read == False  # noqa: E712
        )
    ).one()


@router.get("/unread-count", summary="จำนวนแจ้งเตือนที่ยังไม่อ่าน (หน้าเว็บ poll ทุก 15 วินาที)")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    settle_due_loans(db)
    return {"unread": _unread_count(db, user.id)}


@router.post("/{notification_id}/read", summary="ทำเครื่องหมายว่าอ่านแล้ว")
def mark_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    record = db.get(Notification, notification_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="ไม่พบแจ้งเตือนนี้")
    record.is_read = True
    db.add(record)
    db.commit()
    return {"unread": _unread_count(db, user.id)}


@router.post("/read-all", summary="อ่านแจ้งเตือนทั้งหมดแล้ว")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    db.exec(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    db.commit()
    return {"unread": 0}

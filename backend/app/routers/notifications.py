# Router + Notification service (journey ขั้นตอน 6: แจ้งเตือนความคืบหน้า ไม่ต้องโทรถามโชว์รูม)
# service นี้ไม่ถูกเรียกตรง ๆ จาก router อื่น — สมัครรับ event จาก events.py แล้วสร้างแจ้งเตือนเอง
#
# ส่งถึงหน้าเว็บได้ 2 ทาง:
#   - pull (poll): GET /api/notifications, /unread-count — เบราว์เซอร์ถามเองเป็นรอบ ๆ ใช้เป็น fallback
#   - push (SSE):  GET /api/notifications/stream — เซิร์ฟเวอร์ดันแจ้งเตือนใหม่ให้ทันที ไม่ต้องรอรอบ poll
import asyncio
import hashlib
import json
import secrets
from datetime import datetime, timedelta

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlmodel import Session, func, select, update

from ..data import POINTS_EARN
from ..database import engine, get_session
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


@subscribe("testdrive.completed")
def _on_testdrive_completed(db, record, **_):
    # ไม่มาตามนัด (no_show) ก็ใช้ event เดียวกัน แต่ไม่ต้องขอบคุณ/ชวนรีวิว
    if record.status != "completed":
        return
    notify(db, record.user_id, "testdrive.completed", "ขอบคุณที่มาทดลองขับ",
           f"นัดรหัส {record.code} เสร็จสิ้นแล้ว เขียนรีวิวรับ "
           f"{POINTS_EARN['review']:,} คะแนน", f"{AFTER_SALES_PAGE}#reviews")


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


@subscribe("service.completed")
def _on_service_completed(db, record, **_):
    notify(db, record.user_id, "service.completed", "งานบริการเสร็จแล้ว",
           f"นัดรหัส {record.code} ปิดงานเรียบร้อย ขอบคุณที่ใช้บริการศูนย์ ASTRA Motors",
           AFTER_SALES_PAGE)


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


@router.get("/unread-count", summary="จำนวนแจ้งเตือนที่ยังไม่อ่าน (fallback ตอนเปิดสตรีม SSE ไม่ได้ — poll ทุก 15 วินาที)")
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


# ---------- แจ้งเตือนแบบ push (Server-Sent Events) ----------
# ทำไมต้องมี "ตั๋ว" แยกจาก Bearer token:
#   EventSource ของเบราว์เซอร์แนบ HTTP header เองไม่ได้ จึงส่ง Authorization ไปกับสตรีมไม่ได้
#   และ "ห้าม" เอา token ไปใส่ query string เพราะ URL จะไปติด access log ของ proxy/เซิร์ฟเวอร์
#   -> ขอตั๋วอายุสั้น ใช้ครั้งเดียวด้วย Bearer ตามปกติก่อน แล้วเอาตั๋วนั้นไปเปิดสตรีมแทน
TICKET_TTL_SECONDS = 30        # ตั๋วอายุสั้นมาก พอให้เปิดสตรีมทันทีเท่านั้น
STREAM_TICK_SECONDS = 2        # รอบเช็คแจ้งเตือนใหม่
STREAM_HEARTBEAT_SECONDS = 15  # ส่ง comment กันเน็ต/proxy ตัดการเชื่อมต่อที่เงียบเกินไป
STREAM_MAX_SECONDS = 30 * 60   # จำกัดอายุสตรีม แล้วปล่อยให้ EventSource ต่อใหม่เอง (กัน connection ค้าง)

# เก็บตั๋วใน process (เหมือน event bus) ไม่ลงตาราง auth_sessions เพราะเป็นของชั่วคราวคนละชนิดกับ session
# เก็บเฉพาะ SHA-256 ของตั๋วเหมือนที่ security.py ทำกับ token — หน่วยความจำรั่วก็เอาตั๋วไปใช้ไม่ได้
_stream_tickets: dict[str, tuple[int, datetime]] = {}


def _ticket_hash(ticket: str) -> str:
    return hashlib.sha256(ticket.encode("utf-8")).hexdigest()


def _issue_ticket(user_id: int) -> str:
    now_ = datetime.now()
    # เก็บกวาดตั๋วหมดอายุทุกครั้งที่ออกใบใหม่ (dict นี้จึงไม่โตไม่หยุด)
    for key, (_, expires_at) in list(_stream_tickets.items()):
        if expires_at < now_:
            del _stream_tickets[key]
    ticket = secrets.token_urlsafe(32)
    _stream_tickets[_ticket_hash(ticket)] = (user_id, now_ + timedelta(seconds=TICKET_TTL_SECONDS))
    return ticket


def _claim_ticket(ticket: str) -> int:
    """ใช้ตั๋ว 1 ครั้งแล้วลบทิ้งทันที — ดักซ้ำ/หมดอายุ/ปลอม คืน 401 ทั้งหมด"""
    found = _stream_tickets.pop(_ticket_hash(ticket), None)
    if found is None:
        raise HTTPException(status_code=401, detail="ตั๋วสตรีมไม่ถูกต้องหรือถูกใช้ไปแล้ว กรุณาขอตั๋วใหม่")
    user_id, expires_at = found
    if expires_at < datetime.now():
        raise HTTPException(status_code=401, detail="ตั๋วสตรีมหมดอายุแล้ว กรุณาขอตั๋วใหม่")
    return user_id


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


def _snapshot(user_id: int, after_id: int) -> tuple[list[dict], int, int]:
    """อ่านสถานะกล่องแจ้งเตือน 1 รอบ — เปิด Session ใหม่สั้น ๆ แล้วปิดทันที

    ห้ามถือ Session ค้างไว้ทั้งสตรีม เพราะสตรีมอยู่นานเป็นนาที จะกิน connection pool จนหมด
    """
    with Session(engine) as db:
        settle_due_loans(db)   # ผลสินเชื่อที่ครบเวลาแล้วต้องกลายเป็นแจ้งเตือนก่อนเช็ค
        rows = db.exec(
            select(Notification)
            .where(Notification.user_id == user_id, Notification.id > after_id)
            .order_by(Notification.id)
        ).all()
        fresh = [
            {
                "id": r.id,
                "kind": r.kind,
                "title": r.title,
                "message": r.message,
                "link": r.link,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
        unread = _unread_count(db, user_id)
        last_id = fresh[-1]["id"] if fresh else after_id
        return fresh, unread, last_id


def _latest_id(user_id: int) -> int:
    with Session(engine) as db:
        return db.exec(
            select(func.coalesce(func.max(Notification.id), 0)).where(Notification.user_id == user_id)
        ).one()


@router.post("/stream-ticket", summary="ขอตั๋วอายุสั้นเพื่อเปิดสตรีมแจ้งเตือน (SSE)")
def stream_ticket(user: User = Depends(get_current_user)):
    return {"ticket": _issue_ticket(user.id), "expires_in": TICKET_TTL_SECONDS}


async def _notification_stream(request: Request, user_id: int, max_events: int | None):
    # generator เป็น async + await asyncio.sleep เท่านั้น — time.sleep จะบล็อก event loop
    # ของทั้งแอป (ทุกคนค้าง) ส่วนคิวรี DB เป็น sync จึงโยนไปรันใน thread แยก
    last_id = await anyio.to_thread.run_sync(_latest_id, user_id)
    fresh, unread, last_id = await anyio.to_thread.run_sync(_snapshot, user_id, last_id)

    sent = 0
    yield _sse("unread", {"unread": unread})   # event แรกทันทีที่เชื่อมต่อ หน้าเว็บจะได้ตัวเลขที่ถูกต้องเลย
    sent += 1

    started = datetime.now()
    last_beat = started
    while max_events is None or sent < max_events:
        if (datetime.now() - started).total_seconds() >= STREAM_MAX_SECONDS:
            break
        await asyncio.sleep(STREAM_TICK_SECONDS)
        if await request.is_disconnected():
            break

        fresh, unread, last_id = await anyio.to_thread.run_sync(_snapshot, user_id, last_id)
        if fresh:
            for item in fresh:
                yield _sse("notification", item)
                sent += 1
            yield _sse("unread", {"unread": unread})
            sent += 1
            last_beat = datetime.now()
            continue
        if (datetime.now() - last_beat).total_seconds() >= STREAM_HEARTBEAT_SECONDS:
            yield ": ping\n\n"   # comment ของ SSE — client ไม่เห็นเป็น event แต่ connection ยังมีชีวิต
            last_beat = datetime.now()


@router.get("/stream", summary="สตรีมแจ้งเตือนแบบเรียลไทม์ (SSE) — ต้องมีตั๋วจาก /stream-ticket")
async def stream(
    request: Request,
    ticket: str = Query(..., description="ตั๋วจาก POST /api/notifications/stream-ticket"),
    # ใช้เฉพาะในเทสต์เพื่อให้สตรีมจบเองหลังส่งครบ N event — ค่าปกติคือสตรีมยาวตามปกติ
    max_events: int | None = Query(None, ge=1, include_in_schema=False),
):
    user_id = _claim_ticket(ticket)
    return StreamingResponse(
        _notification_stream(request, user_id, max_events),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # กัน nginx/proxy บัฟเฟอร์ไว้จนแจ้งเตือนไปไม่ถึงทันที
        },
    )

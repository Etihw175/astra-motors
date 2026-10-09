# Router: หลังบ้านสำหรับพนักงานโชว์รูม (Admin console)
# มุมมองข้ามลูกค้าทุกคน จึงปิดด้วย require_admin ทั้ง router — ไม่ใช่ทีละ endpoint (เผลอลืมเส้นเดียวก็ข้อมูลรั่ว)
# ตัวเลขสรุปคิดด้วย SQL aggregate (count/sum/group_by) ไม่ดึงทั้งตารางมานับใน Python
from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, or_, select

from ..crud import loan_dict, reservation_dict, service_dict, testdrive_dict
from ..database import get_session
from ..events import publish
from ..models import Loan, Reservation, ServiceAppointment, TestDrive, User
from ..security import require_admin
from .loans import settle_due_loans

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

TESTDRIVE_STATUSES = ("confirmed", "cancelled", "completed", "no_show")
RESERVATION_STATUSES = ("reserved", "delivery_scheduled", "cancelled")
LOAN_STATUSES = ("reviewing", "approved", "rejected")
SERVICE_STATUSES = ("booked", "cancelled", "completed")


# ---------- ตัวช่วยร่วม ----------

def _parse_date(value: str | None, field: str) -> date_cls | None:
    if value is None or value == "":
        return None
    try:
        return date_cls.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field} ต้องอยู่ในรูป YYYY-MM-DD")


def _check_status(value: str | None, allowed: tuple[str, ...]) -> str | None:
    if value is None or value == "":
        return None
    if value not in allowed:
        raise HTTPException(status_code=400, detail=f"status ต้องเป็นค่าใดค่าหนึ่งใน: {', '.join(allowed)}")
    return value


def _needle(q: str) -> str:
    return f"%{q.strip().lower()}%"


def _page(db: Session, stmt, page: int, per_page: int) -> tuple[list, dict]:
    """แบ่งหน้าด้วย LIMIT/OFFSET ในฐานข้อมูล แล้วคืน (rows, meta) รูปแบบเดียวกับ UserPage"""
    total = db.exec(select(func.count()).select_from(stmt.subquery())).one()
    total_pages = max(1, -(-total // per_page))   # ปัดขึ้น
    rows = db.exec(stmt.offset((page - 1) * per_page).limit(per_page)).all()
    return rows, {"page": page, "per_page": per_page, "total": total, "total_pages": total_pages}


def _group_count(db: Session, table, column) -> dict[str, int]:
    """{status: จำนวน} ในคิวรีเดียว — ใช้แทนการวนนับทั้งตาราง"""
    rows = db.exec(select(column, func.count()).select_from(table).group_by(column)).all()
    return {str(key): int(count) for key, count in rows}


def _count(db: Session, table, *conditions) -> int:
    return int(db.exec(select(func.count()).select_from(table).where(*conditions)).one())


# ---------- 1. ตัวเลขสรุปหน้าแรกของหลังบ้าน ----------

@router.get("/overview", summary="ตัวเลขสรุปสำหรับพนักงานโชว์รูม")
def overview(db: Session = Depends(get_session)):
    """สรุปงานค้างของวันในคิวรีรวม ๆ ไม่กี่ครั้ง — พนักงานเปิดหน้านี้บ่อย จึงต้องเบา"""
    settle_due_loans(db)   # ผลสินเชื่อที่ครบเวลาแล้วต้องนับเข้าสถานะจริง ไม่ใช่ค้างเป็น reviewing
    today = date_cls.today()

    reservation_value = db.exec(
        select(
            func.coalesce(func.sum(Reservation.total_price), 0),
            func.coalesce(func.sum(Reservation.booking_fee), 0),
        ).where(Reservation.status != "cancelled")
    ).one()

    return {
        "members": {
            "total": _count(db, User),
            "customers": _count(db, User, User.role == "customer"),
            "admins": _count(db, User, User.role == "admin"),
        },
        "testdrives": {
            "today": _count(db, TestDrive, TestDrive.status == "confirmed", TestDrive.date == today),
            "upcoming": _count(db, TestDrive, TestDrive.status == "confirmed", TestDrive.date > today),
            "by_status": _group_count(db, TestDrive, TestDrive.status),
        },
        "reservations": {
            "by_status": _group_count(db, Reservation, Reservation.status),
            "active_value": int(reservation_value[0]),      # มูลค่ารวมใบจองที่ยังไม่ยกเลิก
            "booking_fee_received": int(reservation_value[1]),
        },
        "loans": {"by_status": _group_count(db, Loan, Loan.status)},
        "service_appointments": {
            "upcoming": _count(
                db, ServiceAppointment,
                ServiceAppointment.status == "booked", ServiceAppointment.date >= today,
            ),
            "by_status": _group_count(db, ServiceAppointment, ServiceAppointment.status),
        },
    }


# ---------- 2. นัดทดลองขับทั้งหมด ----------

@router.get("/testdrives", summary="นัดทดลองขับทุกสาขา (กรอง + แบ่งหน้า)")
def list_testdrives(
    status: str | None = Query(None, description="confirmed | cancelled | completed | no_show"),
    showroom_id: str | None = Query(None),
    date_from: str | None = Query(None, description="ตั้งแต่วันที่ YYYY-MM-DD"),
    date_to: str | None = Query(None, description="ถึงวันที่ YYYY-MM-DD"),
    q: str | None = Query(None, description="ค้นหาจากรหัสจอง / ชื่อ / เบอร์โทร"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    stmt = select(TestDrive)
    if value := _check_status(status, TESTDRIVE_STATUSES):
        stmt = stmt.where(TestDrive.status == value)
    if showroom_id:
        stmt = stmt.where(TestDrive.showroom_id == showroom_id)
    if start := _parse_date(date_from, "date_from"):
        stmt = stmt.where(TestDrive.date >= start)
    if end := _parse_date(date_to, "date_to"):
        stmt = stmt.where(TestDrive.date <= end)
    if q:
        needle = _needle(q)
        stmt = stmt.where(or_(
            func.lower(TestDrive.code).like(needle),
            func.lower(TestDrive.name).like(needle),
            TestDrive.phone.like(needle),
        ))

    rows, meta = _page(db, stmt.order_by(TestDrive.date, TestDrive.time), page, per_page)
    return {"items": [dict(testdrive_dict(r, db), user_id=r.user_id) for r in rows], **meta}


# ---------- 3. ใบจองรถทั้งหมด ----------

@router.get("/reservations", summary="ใบจองรถทุกใบ (กรอง + แบ่งหน้า)")
def list_reservations(
    status: str | None = Query(None, description="reserved | delivery_scheduled | cancelled"),
    q: str | None = Query(None, description="ค้นหาจากรหัสใบจอง / ชื่อ / เบอร์โทร"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    settle_due_loans(db)
    stmt = select(Reservation)
    if value := _check_status(status, RESERVATION_STATUSES):
        stmt = stmt.where(Reservation.status == value)
    if q:
        needle = _needle(q)
        stmt = stmt.where(or_(
            func.lower(Reservation.code).like(needle),
            func.lower(Reservation.customer_name).like(needle),
            Reservation.customer_phone.like(needle),
        ))

    rows, meta = _page(db, stmt.order_by(Reservation.created_at.desc()), page, per_page)

    # ดึงสถานะสินเชื่อของทั้งหน้าในคิวรีเดียว กัน N+1
    loan_ids = [r.loan_id for r in rows if r.loan_id]
    statuses = dict(db.exec(select(Loan.id, Loan.status).where(Loan.id.in_(loan_ids))).all()) if loan_ids else {}

    items = [
        dict(reservation_dict(r), user_id=r.user_id, loan_status=statuses.get(r.loan_id))
        for r in rows
    ]
    return {"items": items, **meta}


# ---------- 4. คำขอสินเชื่อทั้งหมด ----------

@router.get("/loans", summary="คำขอสินเชื่อทุกใบ (กรอง + แบ่งหน้า)")
def list_loans(
    status: str | None = Query(None, description="reviewing | approved | rejected"),
    q: str | None = Query(None, description="ค้นหาจากรหัสคำขอ / รหัสใบจอง / ชื่อ / เบอร์โทร"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    settle_due_loans(db)
    stmt = select(Loan)
    if value := _check_status(status, LOAN_STATUSES):
        stmt = stmt.where(Loan.status == value)
    if q:
        needle = _needle(q)
        stmt = stmt.where(or_(
            func.lower(Loan.id).like(needle),
            func.lower(Loan.reservation_code).like(needle),
            func.lower(Loan.applicant_name).like(needle),
            Loan.applicant_phone.like(needle),
        ))

    rows, meta = _page(db, stmt.order_by(Loan.created_at.desc()), page, per_page)
    return {"items": [dict(loan_dict(r), user_id=r.user_id) for r in rows], **meta}


# ---------- 5. นัดเข้าศูนย์บริการทั้งหมด ----------

@router.get("/service-appointments", summary="นัดเข้าศูนย์บริการทุกสาขา (กรอง + แบ่งหน้า)")
def list_service_appointments(
    status: str | None = Query(None, description="booked | cancelled | completed"),
    showroom_id: str | None = Query(None),
    date_from: str | None = Query(None, description="ตั้งแต่วันที่ YYYY-MM-DD"),
    date_to: str | None = Query(None, description="ถึงวันที่ YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    stmt = select(ServiceAppointment)
    if value := _check_status(status, SERVICE_STATUSES):
        stmt = stmt.where(ServiceAppointment.status == value)
    if showroom_id:
        stmt = stmt.where(ServiceAppointment.showroom_id == showroom_id)
    if start := _parse_date(date_from, "date_from"):
        stmt = stmt.where(ServiceAppointment.date >= start)
    if end := _parse_date(date_to, "date_to"):
        stmt = stmt.where(ServiceAppointment.date <= end)

    rows, meta = _page(
        db, stmt.order_by(ServiceAppointment.date, ServiceAppointment.time), page, per_page
    )
    return {"items": [dict(service_dict(r, db), user_id=r.user_id) for r in rows], **meta}


# ---------- 6-7. ปิดงานหน้าเคาน์เตอร์ ----------

@router.post("/testdrives/{code}/complete", summary="ปิดนัดทดลองขับ: มาแล้ว หรือ ไม่มาตามนัด")
def complete_testdrive(
    code: str,
    outcome: str = Query("completed", description="completed = มาแล้ว, no_show = ไม่มาตามนัด"),
    db: Session = Depends(get_session),
):
    """ปิดนัดได้เฉพาะวันนัดหรือหลังจากนั้น — ปิดล่วงหน้าคือข้อมูลที่ยังไม่เกิดขึ้นจริง"""
    if outcome not in ("completed", "no_show"):
        raise HTTPException(status_code=400, detail="outcome ต้องเป็น completed หรือ no_show")
    record = db.get(TestDrive, code)
    if record is None:
        raise HTTPException(status_code=404, detail="ไม่พบการจองทดลองขับ")
    if record.status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail=f"นัดนี้อยู่สถานะ {record.status} แล้ว ปิดงานได้เฉพาะนัดที่ยังยืนยันอยู่",
        )
    if record.date > date_cls.today():
        raise HTTPException(status_code=400, detail="ยังไม่ถึงวันนัด ปิดงานล่วงหน้าไม่ได้")

    record.status = outcome
    db.add(record)
    publish(db, "testdrive.completed", record=record)
    db.commit()
    db.refresh(record)
    return testdrive_dict(record, db)


@router.post("/service-appointments/{code}/complete", summary="ปิดงานบริการว่าเสร็จแล้ว")
def complete_service_appointment(code: str, db: Session = Depends(get_session)):
    record = db.get(ServiceAppointment, code)
    if record is None:
        raise HTTPException(status_code=404, detail="ไม่พบนัดหมายนี้")
    if record.status != "booked":
        raise HTTPException(
            status_code=400,
            detail=f"นัดนี้อยู่สถานะ {record.status} แล้ว ปิดงานได้เฉพาะนัดที่ยังรอเข้าศูนย์",
        )

    record.status = "completed"
    db.add(record)
    publish(db, "service.completed", record=record)
    db.commit()
    db.refresh(record)
    return service_dict(record, db)

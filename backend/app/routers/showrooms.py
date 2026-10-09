# Router: โชว์รูมและช่วงเวลาว่างสำหรับทดลองขับ (journey ขั้นตอน 4)
# คิวว่าง = ไม่ชนกับการจองจริงในฐานข้อมูล + ไม่ชนคิว walk-in ที่โชว์รูมจองไว้ (จำลอง)
import hashlib
from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..crud import get_showroom_or_404
from ..data import TESTDRIVE_HOURS
from ..database import get_session
from ..models import Showroom, TestDrive

router = APIRouter(prefix="/api/showrooms", tags=["showrooms"])


def _walk_in_taken(showroom_id: str, date: str, time: str) -> bool:
    """คิวที่พนักงานโชว์รูมรับจองทางโทรศัพท์/หน้าร้าน (ไม่ได้ผ่านเว็บ) — สุ่มแบบคงที่ประมาณ 1 ใน 4"""
    digest = hashlib.md5(f"{showroom_id}|{date}|{time}".encode()).hexdigest()
    return int(digest, 16) % 4 == 0


def booked_times(db: Session, showroom_id: str, day: date_cls) -> set[str]:
    """เวลาที่มีคนจองทดลองขับผ่านระบบไปแล้ว (ไม่นับที่ยกเลิก)"""
    rows = db.exec(
        select(TestDrive.time).where(
            TestDrive.showroom_id == showroom_id,
            TestDrive.date == day,
            TestDrive.status == "confirmed",
        )
    ).all()
    return set(rows)


def is_slot_taken(db: Session, showroom_id: str, day: date_cls, time: str) -> bool:
    return _walk_in_taken(showroom_id, day.isoformat(), time) or time in booked_times(db, showroom_id, day)


# จองล่วงหน้าได้ไกลสุดกี่วัน — คิวที่ไกลกว่านี้โชว์รูมยังจัดตารางพนักงาน/รถสาธิตไม่ได้
# และปล่อยไว้จะมีคิวปี 9999 มาจองค้างระบบ (ยกเลิกไม่ได้เพราะต้องยกเลิกก่อนวันนัด)
MAX_BOOKING_DAYS_AHEAD = 90


def parse_future_date(value: str) -> date_cls:
    """วันที่ต้องอยู่ในรูป YYYY-MM-DD, เป็นวันพรุ่งนี้เป็นต้นไป และไม่เกินเพดานล่วงหน้า"""
    try:
        day = date_cls.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง (ต้องเป็น YYYY-MM-DD)")
    if day <= date_cls.today():
        raise HTTPException(status_code=400, detail="กรุณาเลือกวันล่วงหน้าอย่างน้อย 1 วัน")
    if (day - date_cls.today()).days > MAX_BOOKING_DAYS_AHEAD:
        raise HTTPException(
            status_code=400,
            detail=f"จองล่วงหน้าได้ไม่เกิน {MAX_BOOKING_DAYS_AHEAD} วัน กรุณาเลือกวันที่ใกล้กว่านี้",
        )
    return day


@router.get("")
def list_showrooms(db: Session = Depends(get_session)):
    return db.exec(select(Showroom)).all()


@router.get("/{showroom_id}/slots")
def get_slots(showroom_id: str, date: str, db: Session = Depends(get_session)):
    """คืนช่วงเวลาว่างของโชว์รูมในวันที่เลือก — ช่วงที่ลูกค้าคนอื่นจองแล้วจะไม่ว่างทันที"""
    get_showroom_or_404(db, showroom_id)
    day = parse_future_date(date)
    taken = booked_times(db, showroom_id, day)
    slots = [
        {"time": t, "available": t not in taken and not _walk_in_taken(showroom_id, date, t)}
        for t in TESTDRIVE_HOURS
    ]
    return {"showroom_id": showroom_id, "date": date, "slots": slots}

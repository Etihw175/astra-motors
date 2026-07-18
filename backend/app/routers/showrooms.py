# Router: โชว์รูมและช่วงเวลาว่างสำหรับทดลองขับ (journey ขั้นตอน 4)
import hashlib
from datetime import date as date_cls

from fastapi import APIRouter, HTTPException

from ..data import SHOWROOMS, TESTDRIVE_HOURS

router = APIRouter(prefix="/api/showrooms", tags=["showrooms"])


def _is_slot_taken(showroom_id: str, date: str, time: str) -> bool:
    """สุ่มแบบคงที่ (deterministic) ว่า slot ไหน 'ถูกจองแล้ว' เพื่อจำลองคิวจริง"""
    digest = hashlib.md5(f"{showroom_id}|{date}|{time}".encode()).hexdigest()
    return int(digest, 16) % 4 == 0  # ประมาณ 1 ใน 4 ของ slot จะไม่ว่าง


@router.get("")
def list_showrooms():
    return SHOWROOMS


@router.get("/{showroom_id}/slots")
def get_slots(showroom_id: str, date: str):
    """คืนช่วงเวลาว่างของโชว์รูมในวันที่เลือก — วันในอดีตจองไม่ได้ (edge case)"""
    if not any(s["id"] == showroom_id for s in SHOWROOMS):
        raise HTTPException(status_code=404, detail="ไม่พบโชว์รูม")
    try:
        requested = date_cls.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="รูปแบบวันที่ไม่ถูกต้อง (ต้องเป็น YYYY-MM-DD)")
    if requested <= date_cls.today():
        raise HTTPException(status_code=400, detail="กรุณาเลือกวันล่วงหน้าอย่างน้อย 1 วัน")

    slots = [
        {"time": t, "available": not _is_slot_taken(showroom_id, date, t)}
        for t in TESTDRIVE_HOURS
    ]
    return {"showroom_id": showroom_id, "date": date, "slots": slots}

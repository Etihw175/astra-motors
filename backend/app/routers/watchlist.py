# Router: รายการที่สนใจ (watchlist) — ส่วนหนึ่งของ Catalog service (journey ขั้นที่ 1-2 รับรู้/ค้นหา)
# ปัญหาที่แก้: ลูกค้าซูเปอร์คาร์ส่วนใหญ่ "ยังไม่พร้อมซื้อ" ในการเข้าเว็บครั้งแรก
# ถ้าไม่มีที่เก็บรุ่นที่ถูกใจ เขาจะปิดแท็บแล้วไม่กลับมา — รายการที่สนใจคือเหตุผลให้กลับมา
# และเป็นฐานให้ Notification service เตือน "โปรฯ ของรุ่นที่คุณสนใจใกล้หมด" ได้ตรงคน
from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select

from ..crud import car_dict, get_car_or_404, promo_status, rating_map
from ..database import get_session
from ..models import Car, User, WatchlistItem
from ..schemas import WatchlistCreate
from ..security import get_current_user

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


def watched_car_ids(db: Session, user_id: int) -> list[str]:
    """รหัสรถที่ผู้ใช้คนนี้ติดตาม — คิวรีเดียว ใช้ index ix_watchlist_items_user_id"""
    return list(db.exec(
        select(WatchlistItem.car_id).where(WatchlistItem.user_id == user_id)
        .order_by(WatchlistItem.id.desc())
    ).all())


@router.get("/ids", summary="รหัสรถที่ฉันติดตาม (ใช้ระบายสีปุ่มหัวใจในหน้าแรก)")
def list_watchlist_ids(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    """คืนแค่ list ของ car_id — หน้าแรกมีการ์ดรถทุกรุ่น ขอทีเดียวแล้วเทียบในหน้าเว็บเอง
    ถูกกว่าการยิงถามทีละการ์ด และเบากว่า GET /api/watchlist ที่ลากข้อมูลรถทั้งก้อนมาด้วย
    """
    return watched_car_ids(db, user.id)


@router.get("", summary="รถที่ฉันติดตาม + สถานะโปรโมชั่น")
def list_watchlist(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    """ติดตามล่าสุดขึ้นก่อน พร้อมข้อมูลรถเต็ม (ใช้ car_dict/rating_map ชุดเดียวกับหน้าแคตตาล็อก)"""
    rows = db.exec(
        select(WatchlistItem, Car).join(Car, Car.id == WatchlistItem.car_id)
        .where(WatchlistItem.user_id == user.id)
        .order_by(WatchlistItem.id.desc())
    ).all()
    ratings = rating_map(db) if rows else {}
    return [
        {
            "car": car_dict(car, ratings),
            "promotion": promo_status(car),
            "added_at": item.created_at.isoformat(),
        }
        for item, car in rows
    ]


@router.post("", summary="เพิ่มรถเข้ารายการที่สนใจ (กดซ้ำได้ ผลลัพธ์เหมือนเดิม)")
def add_to_watchlist(
    body: WatchlistCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """กดซ้ำตอบ 200 ไม่ใช่ 409 โดยเจตนา: ปุ่มหัวใจเป็นปุ่มสลับสถานะ

    ผู้ใช้เปิดเว็บไว้สองแท็บแล้วกดติดตามรุ่นเดียวกัน ไม่ถือว่าทำผิด — ผลที่ต้องการคือ
    "รุ่นนี้อยู่ในรายการ" ซึ่งก็เป็นจริงแล้ว ถ้าตอบ error หน้าเว็บจะเด้ง toast แดงทั้งที่สำเร็จ
    """
    car = get_car_or_404(db, body.car_id)
    exists = db.exec(
        select(WatchlistItem).where(WatchlistItem.user_id == user.id, WatchlistItem.car_id == car.id)
    ).first()
    if exists is None:
        db.add(WatchlistItem(user_id=user.id, car_id=car.id))
        db.commit()
    return {"car_id": car.id, "watching": True, "promotion": promo_status(car)}


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT, summary="เอารถออกจากรายการที่สนใจ")
def remove_from_watchlist(
    car_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """ลบสิ่งที่ไม่มีอยู่ก็ตอบ 204 — ปลายทางที่ต้องการคือ "รุ่นนี้ไม่อยู่ในรายการ" ซึ่งเป็นจริงทั้งสองกรณี
    (กดหัวใจรัว ๆ หรือกดจากแท็บที่ข้อมูลเก่า จะได้ไม่เจอ error ทั้งที่สถานะถูกต้องแล้ว)
    """
    record = db.exec(
        select(WatchlistItem).where(WatchlistItem.user_id == user.id, WatchlistItem.car_id == car_id)
    ).first()
    if record is not None:
        db.delete(record)
        db.commit()

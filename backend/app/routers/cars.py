# Router: แคตตาล็อกรถ (journey ขั้นตอน 1-3 รับรู้ / ค้นหา / ดูรายละเอียด)
# ค้นหา + กรอง + เรียงลำดับทำในฐานข้อมูล (WHERE / ORDER BY) ไม่ได้ดึงทั้งหมดมากรองทีหลัง
from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, or_, select

from ..crud import car_dict, get_car_or_404, rating_map
from ..database import get_session
from ..models import Car

router = APIRouter(prefix="/api", tags=["catalog"])

DRIVE_LABELS = {"awd": "ขับเคลื่อน 4 ล้อ (AWD)", "rwd": "ขับเคลื่อนล้อหลัง (RWD)"}

SORTS = {
    "price_asc": Car.price.asc(),
    "price_desc": Car.price.desc(),
    "power_desc": Car.power_hp.desc(),
    "accel_asc": Car.accel.asc(),
}


@router.get("/cars", summary="รายการรถ + ค้นหา/กรอง/เรียงลำดับ")
def list_cars(
    q: str | None = Query(None, description="ค้นหาจากชื่อรุ่น ยี่ห้อ หรือคำโปรย"),
    brand: str | None = Query(None, description="กรองตามยี่ห้อ เช่น Ferrari"),
    drive: str | None = Query(None, description="ระบบขับเคลื่อน: awd หรือ rwd"),
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    seats: int | None = Query(None, ge=1, description="จำนวนที่นั่งขั้นต่ำ"),
    sort: str | None = Query(None, description="price_asc | price_desc | power_desc | accel_asc | rating_desc"),
    db: Session = Depends(get_session),
):
    """ไม่ส่งพารามิเตอร์ = คืนรถทุกรุ่น (หน้าแรก/หน้าเปรียบเทียบใช้แบบนี้)"""
    if sort and sort not in SORTS and sort != "rating_desc":
        raise HTTPException(status_code=400, detail="รูปแบบการเรียงลำดับไม่ถูกต้อง")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="ราคาต่ำสุดต้องไม่มากกว่าราคาสูงสุด")

    stmt = select(Car)
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(
            func.lower(Car.name).like(needle),
            func.lower(Car.brand).like(needle),
            func.lower(Car.tagline).like(needle),
            func.lower(Car.body).like(needle),
        ))
    if brand:
        stmt = stmt.where(func.lower(Car.brand) == brand.strip().lower())
    if drive:
        stmt = stmt.where(Car.drive_code == drive)
    if min_price is not None:
        stmt = stmt.where(Car.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Car.price <= max_price)
    if seats is not None:
        stmt = stmt.where(Car.seats >= seats)
    stmt = stmt.order_by(SORTS.get(sort, Car.price.asc()))

    ratings = rating_map(db)
    cars = [car_dict(c, ratings) for c in db.exec(stmt).all()]
    if sort == "rating_desc":
        cars.sort(key=lambda c: (c["rating"]["avg"] or 0, c["rating"]["count"]), reverse=True)
    return cars


@router.get("/cars/facets", summary="ตัวเลือกสำหรับตัวกรองในหน้าค้นหา")
def facets(db: Session = Depends(get_session)):
    """คืนยี่ห้อ ระบบขับเคลื่อน และช่วงราคาที่มีอยู่จริงในแคตตาล็อก — หน้าเว็บจะได้ไม่ต้อง hardcode"""
    brands = db.exec(select(Car.brand).distinct().order_by(Car.brand)).all()
    drives = db.exec(select(Car.drive_code).distinct().order_by(Car.drive_code)).all()
    low, high = db.exec(select(func.min(Car.price), func.max(Car.price))).one()
    seats = db.exec(select(Car.seats).distinct().order_by(Car.seats)).all()
    return {
        "brands": list(brands),
        "drives": [{"id": d, "label": DRIVE_LABELS.get(d, d)} for d in drives],
        "price": {"min": low or 0, "max": high or 0},
        "seats": list(seats),
        "sorts": [
            {"id": "price_asc", "label": "ราคาต่ำ → สูง"},
            {"id": "price_desc", "label": "ราคาสูง → ต่ำ"},
            {"id": "power_desc", "label": "แรงม้ามากสุด"},
            {"id": "accel_asc", "label": "0–100 เร็วสุด"},
            {"id": "rating_desc", "label": "คะแนนรีวิวสูงสุด"},
        ],
    }


@router.get("/cars/{car_id}", summary="ข้อมูลรถรุ่นเดียว")
def get_car(car_id: str, db: Session = Depends(get_session)):
    """คืนข้อมูลรถรุ่นเดียวสำหรับหน้ารายละเอียด (รวมคะแนนรีวิวเฉลี่ย)"""
    return car_dict(get_car_or_404(db, car_id), rating_map(db))


@router.get("/promotions", summary="โปรโมชั่นที่ยังไม่หมดอายุ")
def promotions(
    include_expired: bool = Query(False, description="แสดงโปรฯ ที่หมดอายุแล้วด้วย"),
    db: Session = Depends(get_session),
):
    """รวมโปรโมชั่นของทุกรุ่นไว้ที่เดียว (journey ขั้นตอน 1: ข้อมูลกระจัดกระจาย)"""
    today = date_cls.today()
    items = []
    for car in db.exec(select(Car).order_by(Car.price)).all():
        if not car.promotion:
            continue
        expires = date_cls.fromisoformat(car.promotion["expires"])
        active = expires >= today
        if not active and not include_expired:
            continue
        items.append({
            "car_id": car.id,
            "car_name": car.name,
            "title": car.promotion["title"],
            "expires": car.promotion["expires"],
            "days_left": (expires - today).days if active else 0,
            "active": active,
        })
    items.sort(key=lambda p: (not p["active"], p["days_left"]))
    return items

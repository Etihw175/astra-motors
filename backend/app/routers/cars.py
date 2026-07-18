# Router: ข้อมูลรุ่นรถ (journey ขั้นตอน 1-2 หน้าเปรียบเทียบ/รายละเอียดรุ่น)
from fastapi import APIRouter, HTTPException

from ..data import CARS

router = APIRouter(prefix="/api/cars", tags=["cars"])


@router.get("")
def list_cars():
    """คืนรายการรถทุกรุ่นสำหรับหน้าแรกและหน้าเปรียบเทียบ"""
    return CARS


@router.get("/{car_id}")
def get_car(car_id: str):
    """คืนข้อมูลรถรุ่นเดียวสำหรับหน้ารายละเอียด"""
    for car in CARS:
        if car["id"] == car_id:
            return car
    raise HTTPException(status_code=404, detail="ไม่พบรุ่นรถที่ต้องการ")

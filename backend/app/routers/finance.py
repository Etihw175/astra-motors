# Router: แผนสินเชื่อสำหรับเครื่องคำนวณไฟแนนซ์ (journey ขั้นตอน 3)
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..crud import plan_dict
from ..database import get_session
from ..models import FinancePlan

router = APIRouter(prefix="/api/finance", tags=["finance"])


@router.get("/plans")
def list_plans(db: Session = Depends(get_session)):
    """คืนแผนสินเชื่อทุกแผน — frontend นำไปคำนวณยอดผ่อนต่อเดือนเอง"""
    return [plan_dict(p) for p in db.exec(select(FinancePlan).order_by(FinancePlan.flat_rate)).all()]

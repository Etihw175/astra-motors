# Router: แผนสินเชื่อสำหรับเครื่องคำนวณไฟแนนซ์ (journey ขั้นตอน 3)
from fastapi import APIRouter

from ..data import FINANCE_PLANS

router = APIRouter(prefix="/api/finance", tags=["finance"])


@router.get("/plans")
def list_plans():
    """คืนแผนสินเชื่อทุกแผน — frontend นำไปคำนวณยอดผ่อนต่อเดือนเอง"""
    return FINANCE_PLANS

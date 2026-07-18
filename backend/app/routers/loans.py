# Router: ยื่นขอสินเชื่อ + ติดตามผลอนุมัติ (journey ขั้นตอน 7)
# จำลองการพิจารณา: สถานะ "reviewing" ประมาณ 20 วินาที แล้วตัดสินจากภาระผ่อนเทียบรายได้
from datetime import datetime

from fastapi import APIRouter, HTTPException

from ..data import FINANCE_PLANS
from ..schemas import LoanCreate
from .bookings import RESERVATIONS

router = APIRouter(prefix="/api/loans", tags=["loans"])

LOANS: dict[str, dict] = {}
_counter = {"loan": 0}

REVIEW_SECONDS = 20          # เวลารอผลจำลอง
MAX_INSTALLMENT_RATIO = 0.40  # ยอดผ่อนต้องไม่เกิน 40% ของรายได้ต่อเดือน


def _monthly_payment(principal: int, flat_rate: float, term_months: int) -> int:
    """คำนวณยอดผ่อนต่อเดือนแบบดอกเบี้ยคงที่ (flat rate)"""
    years = term_months / 12
    interest_total = principal * (flat_rate / 100) * years
    return round((principal + interest_total) / term_months)


@router.post("", status_code=201)
def create_loan(body: LoanCreate):
    reservation = RESERVATIONS.get(body.reservation_code)
    if not reservation:
        raise HTTPException(status_code=404, detail="ไม่พบใบจองรหัสนี้ กรุณาจองรถก่อนยื่นสินเชื่อ")
    if reservation["status"] == "cancelled":
        raise HTTPException(status_code=400, detail="ใบจองนี้ถูกยกเลิกแล้ว")
    if not body.consent_pdpa:
        raise HTTPException(status_code=400, detail="ต้องยินยอมให้ใช้ข้อมูลตาม PDPA ก่อนยื่นสินเชื่อ")

    plan = next((p for p in FINANCE_PLANS if p["id"] == body.plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail="ไม่พบแผนสินเชื่อ")
    if body.term_months not in plan["terms"]:
        raise HTTPException(status_code=400, detail="ระยะเวลาผ่อนไม่ตรงกับแผนที่เลือก")

    total_price = reservation["total_price"]
    if body.down_payment >= total_price:
        raise HTTPException(status_code=400, detail="เงินดาวน์ต้องน้อยกว่าราคารถ")
    down_pct = body.down_payment / total_price * 100
    if down_pct < plan["min_down_pct"]:
        raise HTTPException(
            status_code=400,
            detail=f"แผน {plan['name']} ต้องดาวน์ขั้นต่ำ {plan['min_down_pct']}% "
                   f"(ปัจจุบัน {down_pct:.1f}%)",
        )

    principal = total_price - body.down_payment
    monthly = _monthly_payment(principal, plan["flat_rate"], body.term_months)

    _counter["loan"] += 1
    loan_id = f"LN-{datetime.now():%y%m}-{_counter['loan']:04d}"
    record = {
        "id": loan_id,
        "reservation_code": body.reservation_code,
        "status": "reviewing",  # reviewing -> approved | rejected
        "plan": plan,
        "down_payment": body.down_payment,
        "down_pct": round(down_pct, 1),
        "principal": principal,
        "term_months": body.term_months,
        "monthly_payment": monthly,
        "monthly_income": body.monthly_income,
        "applicant": {"name": body.name, "phone": body.phone, "occupation": body.occupation},
        "documents": body.documents,
        "created_at": datetime.now().isoformat(),
        "result": None,
    }
    LOANS[loan_id] = record
    reservation["loan_id"] = loan_id
    return record


@router.get("/{loan_id}")
def get_loan(loan_id: str):
    """เช็คสถานะสินเชื่อ — frontend เรียกซ้ำ (poll) จนกว่าจะทราบผล"""
    record = LOANS.get(loan_id)
    if not record:
        raise HTTPException(status_code=404, detail="ไม่พบใบคำขอสินเชื่อ")

    if record["status"] == "reviewing":
        elapsed = (datetime.now() - datetime.fromisoformat(record["created_at"])).total_seconds()
        if elapsed >= REVIEW_SECONDS:
            ratio = record["monthly_payment"] / record["monthly_income"]
            if ratio <= MAX_INSTALLMENT_RATIO:
                record["status"] = "approved"
                record["result"] = {
                    "message": "สินเชื่อได้รับการอนุมัติ กรุณานัดวันรับรถและเตรียมเอกสาร",
                }
            else:
                # Edge case: สินเชื่อไม่ผ่าน — เสนอทางเลือกให้ลูกค้า
                record["status"] = "rejected"
                record["result"] = {
                    "message": "ภาระผ่อนต่อเดือนสูงเกินเกณฑ์เมื่อเทียบกับรายได้",
                    "ratio_pct": round(ratio * 100),
                    "max_ratio_pct": round(MAX_INSTALLMENT_RATIO * 100),
                    "alternatives": [
                        "เพิ่มเงินดาวน์ เพื่อลดยอดจัดไฟแนนซ์และยอดผ่อนต่อเดือน",
                        "เพิ่มผู้กู้ร่วม (co-borrower) เพื่อเพิ่มฐานรายได้รวม",
                        "เลือกสถาบันการเงินอื่นที่รองรับระยะผ่อนยาวขึ้น (สูงสุด 84 งวด)",
                    ],
                }
    return record

# Router: ยื่นขอสินเชื่อ + ติดตามผลอนุมัติ (journey ขั้นตอน 5-6)
# จำลองการพิจารณา: สถานะ "reviewing" ประมาณ 20 วินาที แล้วตัดสินจากภาระผ่อนเทียบรายได้
# ผลพิจารณาถูกตัดสินครั้งเดียวแล้วบันทึกลงฐานข้อมูล พร้อมส่ง event loan.decided ให้ระบบแจ้งเตือน
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..crud import get_owned_reservation, loan_dict, new_code
from ..database import get_session
from ..events import publish
from ..models import Document, FinancePlan, Loan, User, now
from ..schemas import LoanCreate
from ..security import can_touch, get_current_user

router = APIRouter(prefix="/api/loans", tags=["loans"])

REVIEW_SECONDS = 20          # เวลารอผลจำลอง
MAX_INSTALLMENT_RATIO = 0.40  # ยอดผ่อนต้องไม่เกิน 40% ของรายได้ต่อเดือน


def _monthly_payment(principal: int, flat_rate: float, term_months: int) -> int:
    """คำนวณยอดผ่อนต่อเดือนแบบดอกเบี้ยคงที่ (flat rate)"""
    years = term_months / 12
    interest_total = principal * (flat_rate / 100) * years
    return round((principal + interest_total) / term_months)


def _affordable_principal(income: int, flat_rate: float, term_months: int) -> int:
    """ยอดจัดไฟแนนซ์สูงสุดที่ยังผ่อนไม่เกิน 40% ของรายได้ต่อเดือน (แก้สมการ flat rate ย้อนกลับ)"""
    budget = income * MAX_INSTALLMENT_RATIO * term_months
    return int(budget / (1 + flat_rate / 100 * term_months / 12))


def _build_alternatives(db: Session, record: Loan) -> list[str]:
    """สินเชื่อไม่ผ่าน — คำนวณทางเลือกเป็นตัวเลขจริง ไม่ใช่คำแนะนำลอย ๆ"""
    plan = record.plan
    income = record.monthly_income
    car_price = record.down_payment + record.principal   # ราคารถที่ล็อกไว้ในใบจองนี้
    options: list[str] = []

    # ทางเลือกที่ 1: เพิ่มเงินดาวน์ (ปัดขึ้นหลักหมื่นให้เป็นตัวเลขที่คุยกันจริงได้)
    #
    # ต้องกัน 2 อย่าง ไม่งั้นคำแนะนำกลายเป็นเรื่องไร้สาระเมื่อรายได้ต่ำมาก:
    #   - ดาวน์รวมต้องยังน้อยกว่าราคารถ (ดาวน์ 10,505,000 บาทของรถ 10,500,000 บาท = ซื้อสดแล้ว
    #     ไม่ใช่ "ทางเลือกสินเชื่อ")
    #   - ยอดผ่อนใหม่ต้องเป็นบวก (ของเดิมเคยเสนอ "ยอดผ่อนจะลดเหลือประมาณ -92 บาท/เดือน")
    affordable = _affordable_principal(income, plan["flat_rate"], record.term_months)
    if 0 < affordable < record.principal:
        extra_down = record.principal - affordable
        extra_down = -(-extra_down // 10_000) * 10_000
        total_down = record.down_payment + extra_down
        new_monthly = _monthly_payment(max(record.principal - extra_down, 0),
                                       plan["flat_rate"], record.term_months)
        if total_down < car_price and new_monthly > 0:
            options.append(
                f"เพิ่มเงินดาวน์อีกประมาณ {extra_down:,} บาท "
                f"(รวมดาวน์ {total_down:,} บาท) "
                f"ยอดผ่อนจะลดเหลือประมาณ {new_monthly:,} บาท/เดือน"
            )

    # ทางเลือกที่ 2: ยืดงวดผ่อนให้ยาวขึ้นภายในแผนเดิม
    for term in sorted(plan["terms"]):
        if term <= record.term_months:
            continue
        monthly = _monthly_payment(record.principal, plan["flat_rate"], term)
        if monthly <= income * MAX_INSTALLMENT_RATIO:
            options.append(
                f"ยืดระยะผ่อนจาก {record.term_months} งวด เป็น {term} งวด "
                f"ยอดผ่อนจะเหลือประมาณ {monthly:,} บาท/เดือน"
            )
            break

    # ทางเลือกที่ 3: เปลี่ยนไปสถาบันที่ดอกเบี้ยต่ำกว่าและผ่านเกณฑ์
    for other in db.exec(select(FinancePlan).order_by(FinancePlan.flat_rate)).all():
        if other.id == plan["id"]:
            continue
        term = max(other.terms)
        monthly = _monthly_payment(record.principal, other.flat_rate, term)
        if monthly <= income * MAX_INSTALLMENT_RATIO:
            options.append(
                f"เปลี่ยนไปแผน {other.name} ดอกเบี้ย {other.flat_rate}% ผ่อน {term} งวด "
                f"ยอดผ่อนประมาณ {monthly:,} บาท/เดือน"
            )
            break

    if not options:
        # รายได้ต่ำกว่าราคารถมากจนปรับตัวเลขอย่างไรก็ไม่ผ่าน — พูดตรง ๆ ดีกว่าเสนอตัวเลขเพ้อฝัน
        options.append(
            f"รายได้ที่แจ้ง ({income:,} บาท/เดือน) ต่ำกว่าเกณฑ์ของรุ่นนี้มาก "
            f"ปรับเงินดาวน์หรือจำนวนงวดแล้วก็ยังไม่ผ่าน "
            f"แนะนำพิจารณารุ่นที่ราคาต่ำกว่า หรือเพิ่มผู้กู้ร่วมเพื่อเพิ่มฐานรายได้รวม"
        )
        return options

    options.append("เพิ่มผู้กู้ร่วม (co-borrower) เพื่อเพิ่มฐานรายได้รวมในการพิจารณา")
    return options


def _decide(db: Session, record: Loan) -> None:
    ratio = record.monthly_payment / record.monthly_income
    if ratio <= MAX_INSTALLMENT_RATIO:
        record.status = "approved"
        record.result = {
            "message": "สินเชื่อได้รับการอนุมัติ กรุณานัดวันรับรถและเตรียมเอกสาร",
        }
    else:
        # Edge case: สินเชื่อไม่ผ่าน — เสนอทางเลือกให้ลูกค้า
        record.status = "rejected"
        record.result = {
            "message": "ภาระผ่อนต่อเดือนสูงเกินเกณฑ์เมื่อเทียบกับรายได้",
            "ratio_pct": round(ratio * 100),
            "max_ratio_pct": round(MAX_INSTALLMENT_RATIO * 100),
            "max_monthly_affordable": round(record.monthly_income * MAX_INSTALLMENT_RATIO),
            "alternatives": _build_alternatives(db, record),
        }
    record.decided_at = now()
    db.add(record)
    publish(db, "loan.decided", record=record)


def settle_due_loans(db: Session) -> int:
    """ตัดสินคำขอที่รอครบเวลาแล้วทั้งหมด (เรียกจากทุกหน้าที่แสดงสถานะ) — คืนจำนวนที่ตัดสิน"""
    due_before = datetime.now() - timedelta(seconds=REVIEW_SECONDS)
    pending = db.exec(
        select(Loan).where(Loan.status == "reviewing", Loan.created_at <= due_before)
    ).all()
    for record in pending:
        _decide(db, record)
    if pending:
        db.commit()
    return len(pending)


@router.post("", status_code=201)
def create_loan(
    body: LoanCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    reservation = get_owned_reservation(db, body.reservation_code, user)
    if reservation.status == "cancelled":
        raise HTTPException(status_code=400, detail="ใบจองนี้ถูกยกเลิกแล้ว")
    if reservation.status == "delivery_scheduled":
        raise HTTPException(status_code=400, detail="ใบจองนี้นัดรับรถแล้ว ไม่ต้องยื่นสินเชื่อเพิ่ม")
    if not body.consent_pdpa:
        raise HTTPException(status_code=400, detail="ต้องยินยอมให้ใช้ข้อมูลตาม PDPA ก่อนยื่นสินเชื่อ")

    # ยื่นซ้ำได้เฉพาะเมื่อคำขอเดิมไม่ผ่าน (กันยื่นซ้อนระหว่างรอผล/หลังอนุมัติ)
    if reservation.loan_id:
        settle_due_loans(db)
        previous = db.get(Loan, reservation.loan_id)
        if previous and previous.status == "reviewing":
            raise HTTPException(status_code=409, detail="มีคำขอสินเชื่อที่กำลังพิจารณาอยู่แล้ว")
        if previous and previous.status == "approved":
            raise HTTPException(status_code=409, detail="สินเชื่อของใบจองนี้อนุมัติแล้ว")

    plan = db.get(FinancePlan, body.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="ไม่พบแผนสินเชื่อ")
    if body.term_months not in plan.terms:
        raise HTTPException(status_code=400, detail="ระยะเวลาผ่อนไม่ตรงกับแผนที่เลือก")

    total_price = reservation.total_price
    if body.down_payment >= total_price:
        raise HTTPException(status_code=400, detail="เงินดาวน์ต้องน้อยกว่าราคารถ")
    down_pct = body.down_payment / total_price * 100
    if down_pct < plan.min_down_pct:
        raise HTTPException(
            status_code=400,
            detail=f"แผน {plan.name} ต้องดาวน์ขั้นต่ำ {plan.min_down_pct}% "
                   f"(ปัจจุบัน {down_pct:.1f}%)",
        )

    # เอกสารแนบต้องเป็นไฟล์ที่ผู้ใช้คนนี้อัปโหลดเองเท่านั้น
    documents = []
    for doc_id in dict.fromkeys(body.document_ids):
        doc = db.get(Document, doc_id)
        if doc is None or doc.user_id != user.id:
            raise HTTPException(status_code=400, detail="ไม่พบเอกสารแนบ กรุณาอัปโหลดใหม่อีกครั้ง")
        documents.append({"id": doc.id, "kind": doc.kind, "filename": doc.filename, "size": doc.size})

    principal = total_price - body.down_payment
    record = Loan(
        id=new_code("LN"),
        reservation_code=reservation.code,
        user_id=user.id,
        plan_id=plan.id,
        plan=plan.model_dump(),
        down_payment=body.down_payment,
        down_pct=round(down_pct, 1),
        principal=principal,
        term_months=body.term_months,
        monthly_payment=_monthly_payment(principal, plan.flat_rate, body.term_months),
        monthly_income=body.monthly_income,
        applicant_name=body.name.strip(),
        applicant_phone=body.phone.strip(),
        occupation=body.occupation,
        documents=documents,
    )
    db.add(record)
    reservation.loan_id = record.id
    db.add(reservation)
    publish(db, "loan.submitted", record=record)
    db.commit()
    db.refresh(record)
    return loan_dict(record)


@router.get("/{loan_id}")
def get_loan(
    loan_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """เช็คสถานะสินเชื่อ — frontend เรียกซ้ำ (poll) จนกว่าจะทราบผล"""
    settle_due_loans(db)
    record = db.get(Loan, loan_id)
    if record is None or not can_touch(user, record.user_id):
        raise HTTPException(status_code=404, detail="ไม่พบใบคำขอสินเชื่อ")
    return loan_dict(record)

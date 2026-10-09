# Router: บริการหลังการขาย (journey ขั้นตอน 7)
# - นัดเข้าศูนย์บริการ: เลือกสาขาที่มีศูนย์บริการ + วัน/เวลา (แต่ละช่วงรับได้ตามจำนวนช่องซ่อม)
# - Loyalty service: สะสมคะแนนจาก event ของ service อื่น (จอง/รีวิว/นัดศูนย์) แล้วแลกของรางวัล
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from ..crud import get_car_or_404, get_showroom_or_404, new_code, service_dict
from ..data import MEMBER_TIERS, POINTS_EARN, REWARDS, SERVICE_BAYS, SERVICE_HOURS, SERVICE_TYPES
from ..database import get_session
from ..events import publish, subscribe
from ..models import PointTransaction, ServiceAppointment, User
from ..schemas import RedeemCreate, ServiceAppointmentCreate
from ..security import can_touch, get_current_user
from .showrooms import parse_future_date

router = APIRouter(prefix="/api", tags=["after-sales"])


# ======================= Loyalty service =======================

def add_points(db: Session, user_id: int | None, points: int, reason: str, ref: str | None = None) -> None:
    if user_id is None or points == 0:
        return
    db.add(PointTransaction(user_id=user_id, points=points, reason=reason, ref=ref))


def _balance(db: Session, user_id: int) -> tuple[int, int]:
    """คืน (คะแนนคงเหลือ, คะแนนที่เคยได้รับทั้งหมด)"""
    balance = db.exec(
        select(func.coalesce(func.sum(PointTransaction.points), 0)).where(PointTransaction.user_id == user_id)
    ).one()
    earned = db.exec(
        select(func.coalesce(func.sum(PointTransaction.points), 0)).where(
            PointTransaction.user_id == user_id, PointTransaction.points > 0
        )
    ).one()
    return int(balance), int(earned)


@subscribe("testdrive.booked")
def _points_testdrive(db, record, car, **_):
    add_points(db, record.user_id, POINTS_EARN["testdrive"], f"จองทดลองขับ {car.name}", record.code)


@subscribe("testdrive.cancelled")
def _points_testdrive_reversed(db, record, **_):
    # ต้องมีคู่กับ _points_testdrive เสมอ ไม่งั้นจอง-ยกเลิกวนซ้ำ ๆ ได้คะแนนฟรีไม่จำกัด
    # (จองพรุ่งนี้ ยกเลิก ทำ 7 รอบ = 700 คะแนน แลกของรางวัลจริงได้) — กติกาเดียวกับใบจอง/รีวิว/นัดศูนย์
    add_points(db, record.user_id, -POINTS_EARN["testdrive"],
               f"หักคืนคะแนน: ยกเลิกนัดทดลองขับ {record.code}", record.code)


@subscribe("reservation.created")
def _points_reservation(db, record, **_):
    add_points(db, record.user_id, POINTS_EARN["reservation"], f"วางเงินจอง {record.car_name}", record.code)


@subscribe("reservation.cancelled")
def _points_reservation_reversed(db, record, **_):
    # ยกเลิกใบจองแล้วหักคะแนนที่ได้จากใบจองนั้นคืน (กันจอง-ยกเลิกเพื่อปั๊มคะแนน)
    add_points(db, record.user_id, -POINTS_EARN["reservation"], f"หักคืนคะแนน: ยกเลิกใบจอง {record.code}",
               record.code)


@subscribe("review.posted")
def _points_review(db, review, car, **_):
    add_points(db, review.user_id, POINTS_EARN["review"], f"เขียนรีวิว {car.name}", f"review-{review.id}")


@subscribe("review.deleted")
def _points_review_reversed(db, review, **_):
    add_points(db, review.user_id, -POINTS_EARN["review"], "หักคืนคะแนน: ลบรีวิว", f"review-{review.id}")


@subscribe("service.booked")
def _points_service(db, record, **_):
    add_points(db, record.user_id, POINTS_EARN["service"], "นัดเข้าศูนย์บริการออนไลน์", record.code)


@router.get("/loyalty", summary="คะแนนสะสม ระดับสมาชิก และของรางวัล")
def loyalty(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    balance, earned = _balance(db, user.id)
    tier = [t for t in MEMBER_TIERS if earned >= t["min"]][-1]
    upcoming = next((t for t in MEMBER_TIERS if t["min"] > earned), None)
    history = db.exec(
        select(PointTransaction).where(PointTransaction.user_id == user.id)
        .order_by(PointTransaction.id.desc()).limit(30)
    ).all()
    return {
        "balance": balance,
        "lifetime_earned": earned,
        "tier": tier,
        "next_tier": ({**upcoming, "points_needed": upcoming["min"] - earned} if upcoming else None),
        "earn_rules": POINTS_EARN,
        "rewards": [{**r, "affordable": balance >= r["points"]} for r in REWARDS],
        "history": history,
    }


@router.post("/loyalty/redeem", summary="แลกคะแนนเป็นของรางวัล")
def redeem(body: RedeemCreate, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    reward = next((r for r in REWARDS if r["id"] == body.reward_id), None)
    if reward is None:
        raise HTTPException(status_code=404, detail="ไม่พบของรางวัลนี้")
    balance, _ = _balance(db, user.id)
    if balance < reward["points"]:
        raise HTTPException(
            status_code=400,
            detail=f"คะแนนไม่พอ ต้องใช้ {reward['points']:,} คะแนน (มีอยู่ {balance:,} คะแนน)",
        )
    voucher = new_code("RW")
    add_points(db, user.id, -reward["points"], f"แลก {reward['name']}", voucher)
    publish(db, "points.redeemed", user_id=user.id, reward=reward, voucher=voucher)
    db.commit()
    return {"voucher": voucher, "reward": reward, "balance": balance - reward["points"]}


# ======================= Service center =======================

def _service_load(db: Session, showroom_id: str, day) -> dict[str, int]:
    """จำนวนรถที่นัดไว้แล้วในแต่ละช่วงเวลา"""
    rows = db.exec(
        select(ServiceAppointment.time, func.count()).where(
            ServiceAppointment.showroom_id == showroom_id,
            ServiceAppointment.date == day,
            ServiceAppointment.status == "booked",
        ).group_by(ServiceAppointment.time)
    ).all()
    return {time: count for time, count in rows}


def _service_center_or_400(db: Session, showroom_id: str):
    showroom = get_showroom_or_404(db, showroom_id)
    if not showroom.service_center:
        raise HTTPException(status_code=400, detail=f"{showroom.name} ไม่มีศูนย์บริการ กรุณาเลือกสาขาอื่น")
    return showroom


@router.get("/service/types", summary="ประเภทบริการที่นัดได้")
def service_types():
    return SERVICE_TYPES


@router.get("/service/slots", summary="ช่วงเวลาว่างของศูนย์บริการ")
def service_slots(showroom_id: str, date: str, db: Session = Depends(get_session)):
    _service_center_or_400(db, showroom_id)
    day = parse_future_date(date)
    load = _service_load(db, showroom_id, day)
    return {
        "showroom_id": showroom_id,
        "date": date,
        "slots": [
            {"time": t, "remaining": SERVICE_BAYS - load.get(t, 0), "available": load.get(t, 0) < SERVICE_BAYS}
            for t in SERVICE_HOURS
        ],
    }


@router.post("/service/appointments", status_code=201, summary="นัดเข้าศูนย์บริการ")
def create_service_appointment(
    body: ServiceAppointmentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    car = get_car_or_404(db, body.car_id)
    _service_center_or_400(db, body.showroom_id)
    if body.service_type not in {s["id"] for s in SERVICE_TYPES}:
        raise HTTPException(status_code=400, detail="ประเภทบริการไม่ถูกต้อง")
    if body.time not in SERVICE_HOURS:
        raise HTTPException(status_code=400, detail="ช่วงเวลาไม่ถูกต้อง")
    day = parse_future_date(body.date)
    if _service_load(db, body.showroom_id, day).get(body.time, 0) >= SERVICE_BAYS:
        raise HTTPException(status_code=409, detail="ช่วงเวลานี้เต็มแล้ว กรุณาเลือกเวลาอื่น")
    # คนเดียวเข้าศูนย์ได้ทีละคัน: ถ้าไม่กัน คนเดียวจองซ้ำจนกินช่องซ่อมหมดทั้งช่วงเวลาได้
    mine = db.exec(
        select(ServiceAppointment.code).where(
            ServiceAppointment.user_id == user.id,
            ServiceAppointment.showroom_id == body.showroom_id,
            ServiceAppointment.date == day,
            ServiceAppointment.time == body.time,
            ServiceAppointment.status == "booked",
        )
    ).first()
    if mine:
        raise HTTPException(status_code=409,
                            detail=f"คุณมีนัดในช่วงเวลานี้อยู่แล้ว (รหัส {mine}) กรุณาเลือกเวลาอื่น")

    record = ServiceAppointment(
        code=new_code("SV"),
        user_id=user.id,
        car_id=car.id,
        showroom_id=body.showroom_id,
        date=day,
        time=body.time,
        service_type=body.service_type,
        mileage_km=body.mileage_km,
        note=body.note.strip(),
    )
    db.add(record)
    publish(db, "service.booked", record=record)
    db.commit()
    db.refresh(record)
    return service_dict(record, db)


@router.get("/service/appointments", summary="นัดเข้าศูนย์ของฉัน")
def my_service_appointments(
    include_cancelled: bool = Query(True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    stmt = select(ServiceAppointment).where(ServiceAppointment.user_id == user.id)
    if not include_cancelled:
        stmt = stmt.where(ServiceAppointment.status == "booked")
    rows = db.exec(stmt.order_by(ServiceAppointment.date, ServiceAppointment.time)).all()
    return [service_dict(r, db) for r in rows]


@router.post("/service/appointments/{code}/cancel", summary="ยกเลิกนัดเข้าศูนย์")
def cancel_service_appointment(
    code: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    record = db.get(ServiceAppointment, code)
    if record is None or not can_touch(user, record.user_id):
        raise HTTPException(status_code=404, detail="ไม่พบนัดหมายนี้")
    if record.status == "cancelled":
        raise HTTPException(status_code=400, detail="นัดหมายนี้ถูกยกเลิกไปแล้ว")
    record.status = "cancelled"
    db.add(record)
    # คะแนนจากการนัดถูกหักคืน ไม่งั้นนัด-ยกเลิกซ้ำ ๆ จะได้คะแนนฟรี
    add_points(db, record.user_id, -POINTS_EARN["service"], f"หักคืนคะแนน: ยกเลิกนัด {record.code}", record.code)
    publish(db, "service.cancelled", record=record)
    db.commit()
    db.refresh(record)
    return service_dict(record, db)

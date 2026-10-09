# Router: รีวิวรถจากผู้ใช้ (journey ขั้นตอน 1 รับรู้ + ขั้นตอน 7 หลังการใช้งาน)
# ใครก็อ่านรีวิวได้ / เขียนได้เฉพาะสมาชิก 1 คน 1 รีวิวต่อรุ่น
# รีวิวจากคนที่เคยทดลองขับหรือจองรุ่นนั้นจริงจะได้ป้าย "ผ่านการใช้งานจริง" (verified)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..crud import get_car_or_404, rating_map
from ..database import get_session
from ..events import publish
from ..models import Car, Reservation, Review, TestDrive, User
from ..schemas import ReviewCreate
from ..security import can_touch, get_current_user, get_optional_user

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def _display_name(user: User | None) -> str:
    """แสดงชื่อแบบปิดนามสกุล เช่น "สมชาย ใ." (ไม่เปิดเผยข้อมูลส่วนตัวเต็ม)"""
    if user is None:
        return "สมาชิกที่ลบบัญชีแล้ว"
    parts = user.full_name.split()
    return f"{parts[0]} {parts[1][0]}." if len(parts) > 1 else parts[0]


def review_dict(review: Review, db: Session, viewer: User | None = None) -> dict:
    """รีวิวในรูปแบบที่เปิดเผยได้

    ไม่ส่ง user_id ของผู้เขียนออกไป: เป็นรหัสภายในที่ทำให้คนนอกเชื่อมรีวิวหลายรุ่นเข้าเป็นคนเดียวกัน
    และนับจำนวนสมาชิกทั้งระบบได้ หน้าเว็บต้องการแค่ "รีวิวนี้ของฉันไหม" จึงคิดให้เป็น is_mine
    (ผู้ดูแลระบบลบรีวิวใครก็ได้อยู่แล้ว จึงเห็น is_mine=True เพื่อให้ปุ่มลบโผล่ตามสิทธิ์จริง)
    """
    car = db.get(Car, review.car_id)
    return {
        "id": review.id,
        "car": {"id": car.id, "name": car.name},
        "rating": review.rating,
        "title": review.title,
        "comment": review.comment,
        "verified": review.verified,
        "author": _display_name(db.get(User, review.user_id)),
        "is_mine": viewer is not None and can_touch(viewer, review.user_id),
        "created_at": review.created_at.isoformat(),
    }


def _has_experience(db: Session, user_id: int, car_id: str) -> bool:
    drove = db.exec(select(TestDrive.code).where(
        TestDrive.user_id == user_id, TestDrive.car_id == car_id)).first()
    bought = db.exec(select(Reservation.code).where(
        Reservation.user_id == user_id, Reservation.car_id == car_id)).first()
    return bool(drove or bought)


@router.get("", summary="รีวิวล่าสุด (กรองตามรุ่นได้)")
def list_reviews(
    car_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    viewer: User | None = Depends(get_optional_user),
    db: Session = Depends(get_session),
):
    """อ่านได้ทุกคน — ล็อกอินอยู่จะได้ธง is_mine มาด้วยเพื่อให้หน้าเว็บแสดงปุ่มลบของตัวเอง"""
    stmt = select(Review)
    if car_id:
        stmt = stmt.where(Review.car_id == car_id)
    rows = db.exec(stmt.order_by(Review.id.desc()).limit(limit)).all()
    return [review_dict(r, db, viewer) for r in rows]


@router.get("/mine", summary="รีวิวที่ฉันเขียน")
def my_reviews(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    rows = db.exec(select(Review).where(Review.user_id == user.id).order_by(Review.id.desc())).all()
    return [review_dict(r, db, user) for r in rows]


@router.get("/summary", summary="คะแนนเฉลี่ยของทุกรุ่น")
def summary(db: Session = Depends(get_session)):
    return rating_map(db)


@router.post("", status_code=201, summary="เขียนรีวิว (+200 คะแนน)")
def create_review(
    body: ReviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    car = get_car_or_404(db, body.car_id)
    exists = db.exec(select(Review).where(Review.user_id == user.id, Review.car_id == car.id)).first()
    if exists:
        raise HTTPException(status_code=409, detail="คุณรีวิวรุ่นนี้ไปแล้ว ลบรีวิวเดิมก่อนถ้าต้องการเขียนใหม่")

    review = Review(
        user_id=user.id,
        car_id=car.id,
        rating=body.rating,
        title=body.title.strip(),
        comment=body.comment.strip(),
        verified=_has_experience(db, user.id, car.id),
    )
    db.add(review)
    db.flush()   # ให้ได้ id ก่อนส่ง event
    publish(db, "review.posted", review=review, car=car)
    db.commit()
    db.refresh(review)
    return review_dict(review, db, user)


@router.delete("/{review_id}", status_code=204, summary="ลบรีวิว (เจ้าของหรือผู้ดูแล)")
def delete_review(
    review_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    review = db.get(Review, review_id)
    if review is None or not can_touch(user, review.user_id):
        raise HTTPException(status_code=404, detail="ไม่พบรีวิวนี้")
    publish(db, "review.deleted", review=review)
    db.delete(review)
    db.commit()

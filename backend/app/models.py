# ตารางในฐานข้อมูล (SQLModel) — 1 class = 1 ตาราง
# จัดกลุ่มตาม service ของระบบ (ดูแผนภาพใน docs/architecture/) แต่ละกลุ่มเป็นเจ้าของตารางของตัวเอง
# ฟิลด์ที่เป็นโครงสร้างซ้อน (สี/ออปชันของรถ, ผลพิจารณาสินเชื่อ) เก็บเป็น JSON
# ใช้ได้ทั้ง PostgreSQL (ใน Docker) และ SQLite (รันในเครื่อง/รันเทสต์)
import datetime as dt
from typing import Optional

from sqlalchemy import JSON, Column, LargeBinary, UniqueConstraint
from sqlmodel import Field, SQLModel


def now() -> dt.datetime:
    return dt.datetime.now().replace(microsecond=0)


# ======================= Identity service =======================

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=20)
    full_name: str = Field(max_length=100)
    email: str = Field(index=True, unique=True, max_length=254)
    phone: str = Field(max_length=15)
    role: str = Field(default="customer", max_length=20)     # customer | admin
    is_active: bool = True
    password_hash: str                                        # pbkdf2_sha256$... ไม่เก็บรหัสผ่านจริง
    created_at: dt.datetime = Field(default_factory=now)
    updated_at: dt.datetime = Field(default_factory=now)


class AuthSession(SQLModel, table=True):
    """session ของ Bearer token — เก็บเฉพาะ SHA-256 ของ token (ฐานข้อมูลรั่วก็เอา token ไปใช้ไม่ได้)"""
    __tablename__ = "auth_sessions"

    token_hash: str = Field(primary_key=True, max_length=64)
    user_id: int = Field(foreign_key="users.id", index=True)
    expires_at: dt.datetime
    created_at: dt.datetime = Field(default_factory=now)


# ======================= Catalog service =======================

class Car(SQLModel, table=True):
    __tablename__ = "cars"

    id: str = Field(primary_key=True, max_length=40)
    name: str
    brand: str = Field(index=True)
    tagline: str
    body: str
    price: int = Field(index=True)
    engine: str
    power_hp: int
    torque_nm: int
    drive: str
    drive_code: str = Field(index=True)                       # awd | rwd ใช้กรองในหน้าค้นหา
    seats: int
    fuel: str
    accel: float
    safety: str
    warranty: str
    colors: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    options: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    promotion: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    road: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class Showroom(SQLModel, table=True):
    __tablename__ = "showrooms"

    id: str = Field(primary_key=True, max_length=40)
    name: str
    address: str
    phone: str
    hours: str
    service_center: bool = True


class FinancePlan(SQLModel, table=True):
    __tablename__ = "finance_plans"

    id: str = Field(primary_key=True, max_length=40)
    name: str
    flat_rate: float
    min_down_pct: int
    terms: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    promo: bool = False
    note: str = ""


# ======================= Booking service =======================

class TestDrive(SQLModel, table=True):
    __tablename__ = "test_drives"

    code: str = Field(primary_key=True, max_length=24)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)  # จองแบบ guest ได้
    car_id: str = Field(foreign_key="cars.id")
    showroom_id: str = Field(foreign_key="showrooms.id", index=True)
    date: dt.date = Field(index=True)
    time: str = Field(max_length=5)
    name: str
    phone: str
    contact_message_only: bool = False
    status: str = "confirmed"                                 # confirmed | cancelled | completed | no_show
    created_at: dt.datetime = Field(default_factory=now)


# ======================= Order service =======================

class Reservation(SQLModel, table=True):
    __tablename__ = "reservations"

    code: str = Field(primary_key=True, max_length=24)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    car_id: str = Field(foreign_key="cars.id")
    car_name: str
    base_price: int
    color: dict = Field(sa_column=Column(JSON, nullable=False))
    options: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    total_price: int
    booking_fee: int
    payment_method: str                                       # promptpay | card (จำลอง)
    promotion: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    promotion_expired: bool = False
    price_locked_until: dt.date
    customer_name: str
    customer_phone: str
    customer_email: str
    contact_message_only: bool = False
    status: str = "reserved"                                  # reserved -> delivery_scheduled | cancelled
    loan_id: Optional[str] = None
    delivery_date: Optional[dt.date] = None
    refund: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: dt.datetime = Field(default_factory=now)


class Document(SQLModel, table=True):
    """ไฟล์เอกสารประกอบสินเชื่อที่ผู้ใช้อัปโหลด (บัตรประชาชน/สลิปเงินเดือน) เก็บเป็น binary"""
    __tablename__ = "documents"

    id: str = Field(primary_key=True, max_length=24)
    user_id: int = Field(foreign_key="users.id", index=True)
    kind: str = Field(max_length=20)                          # id_card | income | other
    filename: str
    content_type: str
    size: int
    data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    created_at: dt.datetime = Field(default_factory=now)


# ======================= Finance service =======================

class Loan(SQLModel, table=True):
    __tablename__ = "loans"

    id: str = Field(primary_key=True, max_length=24)
    reservation_code: str = Field(foreign_key="reservations.code", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    plan_id: str = Field(foreign_key="finance_plans.id")
    plan: dict = Field(sa_column=Column(JSON, nullable=False))  # สำเนาแผน ณ วันยื่น
    status: str = "reviewing"                                 # reviewing -> approved | rejected
    down_payment: int
    down_pct: float
    principal: int
    term_months: int
    monthly_payment: int
    monthly_income: int
    applicant_name: str
    applicant_phone: str
    occupation: str
    documents: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: dt.datetime = Field(default_factory=now)
    decided_at: Optional[dt.datetime] = None


# ======================= After-sales service =======================

class Review(SQLModel, table=True):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("user_id", "car_id", name="uq_review_user_car"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    car_id: str = Field(foreign_key="cars.id", index=True)
    rating: int                                               # 1-5 ดาว
    title: str
    comment: str
    verified: bool = False                                    # เคยทดลองขับ/จองรุ่นนี้จริง
    created_at: dt.datetime = Field(default_factory=now)


class ServiceAppointment(SQLModel, table=True):
    __tablename__ = "service_appointments"

    code: str = Field(primary_key=True, max_length=24)
    user_id: int = Field(foreign_key="users.id", index=True)
    car_id: str = Field(foreign_key="cars.id")
    showroom_id: str = Field(foreign_key="showrooms.id", index=True)
    date: dt.date = Field(index=True)
    time: str = Field(max_length=5)
    service_type: str
    mileage_km: int
    note: str = ""
    status: str = "booked"                                    # booked | cancelled | completed
    created_at: dt.datetime = Field(default_factory=now)


class PointTransaction(SQLModel, table=True):
    """สมุดบัญชีคะแนนสะสม — ยอดคงเหลือ = ผลรวมของ points (บวก=ได้รับ, ลบ=แลก/หักคืน)"""
    __tablename__ = "point_transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    points: int
    reason: str
    ref: Optional[str] = None
    created_at: dt.datetime = Field(default_factory=now)


# ======================= Notification service =======================

class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    kind: str = Field(max_length=40)                          # ชื่อ event ที่ทำให้เกิดการแจ้งเตือน
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool = False
    created_at: dt.datetime = Field(default_factory=now)

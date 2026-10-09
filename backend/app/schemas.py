# Pydantic schemas — รูปแบบข้อมูลรับ-ส่งผ่าน API (validate อัตโนมัติทุก endpoint)
import re
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, EmailStr, Field


# ---------- ชนิดข้อมูลร่วม ----------
# ทำไมต้อง "ตัดช่องว่างก่อนวัดความยาว":
#   min_length ของ Pydantic นับตัวอักษรดิบ ชื่อที่เป็นช่องว่าง 5 ตัวจึงผ่าน
#   แล้วโค้ดใน router ค่อย .strip() ทีหลัง -> ได้ชื่อว่าง "" ลงฐานข้อมูล
#   BeforeValidator ตัดให้ก่อน Pydantic จะวัดความยาว ของว่างเปล่าจึงถูกปฏิเสธที่ชั้น schema เลย
def _stripped(value):
    return value.strip() if isinstance(value, str) else value


Stripped = Annotated[str, BeforeValidator(_stripped)]

# เบอร์โทรไทย: 0 ตามด้วยตัวเลข 8-9 ตัว หรือรูป +66 — ยอมให้มีช่องว่าง/ขีดคั่นแล้วตัดออกให้
# ของเดิมเช็คแค่ความยาว 9-15 ตัว "abcdefghij" จึงสมัครสมาชิกผ่าน แล้วโชว์รูมโทรหาลูกค้าไม่ได้
_PHONE_RE = re.compile(r"\A(0|\+66)\d{8,9}\Z")


def _phone(value):
    if not isinstance(value, str):
        return value
    cleaned = re.sub(r"[\s\-()]", "", value)
    if not _PHONE_RE.fullmatch(cleaned):
        raise ValueError("เบอร์โทรศัพท์ไม่ถูกต้อง (ตัวอย่างที่ใช้ได้: 0812345678)")
    return cleaned


Phone = Annotated[str, BeforeValidator(_phone)]
ContactName = Annotated[Stripped, Field(min_length=2, max_length=100)]


class TestDriveCreate(BaseModel):
    car_id: str
    showroom_id: str
    date: str = Field(..., description="วันที่นัด รูปแบบ YYYY-MM-DD")
    time: str = Field(..., description="เวลานัด เช่น 10:00")
    name: ContactName
    phone: Phone
    has_license: bool = Field(..., description="ยืนยันว่ามีใบขับขี่")
    contact_message_only: bool = Field(False, description="ให้ติดต่อผ่านข้อความเท่านั้น ไม่รับสายโทรศัพท์")


class ReservationCreate(BaseModel):
    car_id: str
    color_id: str
    option_ids: list[str] = []
    name: ContactName
    phone: Phone
    email: EmailStr   # เคยเป็น str ล้วน "xxxxx" จึงผ่าน แล้วส่งใบจองไปไม่ถึงลูกค้า
    payment_method: str = Field(..., description="promptpay หรือ card (จำลอง)")
    contact_message_only: bool = False


class PaymentCreate(BaseModel):
    """เริ่มรายการชำระเงินจอง (payment intent) — ใบจองจะออกหลังยืนยันการชำระเงินแล้วเท่านั้น"""
    car_id: str
    color_id: str
    option_ids: list[str] = []
    name: ContactName
    phone: Phone
    email: EmailStr   # เคยเป็น str ล้วน "xxxxx" จึงผ่าน แล้วส่งใบจองไปไม่ถึงลูกค้า
    method: str = Field(..., description="promptpay หรือ card (จำลองทั้งคู่)")
    contact_message_only: bool = False
    # รับได้แค่ 4 ตัวท้ายเพื่อแสดงผล "•••• 4242" เท่านั้น — ห้ามรับเลขบัตรเต็มเด็ดขาด
    # ระบบจริงต้องให้ payment gateway (Omise/2C2P/Stripe) เก็บเลขบัตรแล้วส่ง token กลับมา
    # ร้านค้าเก็บแต่ token เพื่อไม่ต้องเข้าขอบเขต PCI-DSS เอง
    card_last4: Optional[str] = Field(None, min_length=4, max_length=4,
                                      description="4 ตัวท้ายบัตร (ไม่บังคับ ใช้แสดงผลเท่านั้น)")


class DeliveryCreate(BaseModel):
    date: str = Field(..., description="วันนัดรับรถ รูปแบบ YYYY-MM-DD")


class LoanCreate(BaseModel):
    reservation_code: str
    plan_id: str
    down_payment: int = Field(..., ge=0)
    term_months: int
    name: ContactName
    phone: Phone
    occupation: Annotated[Stripped, Field(min_length=2, max_length=100)]
    monthly_income: int = Field(..., gt=0)
    document_ids: list[str] = Field(default=[], max_length=10,
                                    description="id เอกสารที่อัปโหลดผ่าน POST /api/documents")
    consent_pdpa: bool = Field(..., description="ยินยอมให้ใช้ข้อมูลตาม PDPA")


# ---------- Authentication / User Management ----------
# Pydantic ตรวจความถูกต้องให้อัตโนมัติ ถ้าผิดเงื่อนไข FastAPI ตอบ 422 พร้อมบอกฟิลด์ที่ผิดเอง

class RegisterCreate(BaseModel):
    username: str = Field(..., min_length=4, max_length=20,
                          description="a-z, 0-9, _ และ . เท่านั้น")
    password: str = Field(..., min_length=8, max_length=72)
    full_name: ContactName
    email: EmailStr
    phone: Phone


class LoginCreate(BaseModel):
    username: str = Field(..., min_length=1, description="ใช้ username หรืออีเมลก็ได้")
    password: str = Field(..., min_length=1)


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=72)


class UserUpdate(BaseModel):
    """แก้ไขข้อมูล user — ส่งมาเฉพาะฟิลด์ที่ต้องการแก้ (ฟิลด์ที่ไม่ส่งมาจะไม่ถูกแตะ)"""
    full_name: Optional[ContactName] = None
    email: Optional[EmailStr] = None
    phone: Optional[Phone] = None
    role: Optional[str] = Field(None, description="customer หรือ admin (เฉพาะผู้ดูแลระบบแก้ได้)")
    is_active: Optional[bool] = Field(None, description="ระงับ/เปิดใช้งานบัญชี (เฉพาะผู้ดูแลระบบ)")


class UserOut(BaseModel):
    """รูปแบบข้อมูล user ที่ส่งออก — ไม่มี password_hash เด็ดขาด"""
    id: int
    username: str
    full_name: str
    email: str
    phone: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str


class UserPage(BaseModel):
    """ผลลัพธ์แบบแบ่งหน้า (pagination) ของ GET /api/users"""
    items: list[UserOut]
    page: int
    per_page: int
    total: int
    total_pages: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: UserOut


# ---------- จำลองการใช้งานบนถนนไทย ----------

class SimulationCreate(BaseModel):
    car_id: str
    flood_depth_cm: float = Field(0, ge=0, le=100, description="ระดับน้ำท่วม (ซม.)")
    bump_height_cm: float = Field(0, ge=0, le=40, description="ความสูงของลูกระนาด/ทางลาด (ซม.)")
    road_rough: int = Field(0, ge=0, le=3, description="สภาพผิวถนน 0=เรียบ ถึง 3=ชำรุดหนัก")
    front_lift: bool = Field(False, description="เปิดใช้ระบบยกหน้ารถ (ถ้ารุ่นนั้นมี)")
    km_per_year: int = Field(12000, ge=1000, le=100000, description="ระยะทางที่ใช้ต่อปี (กม.)")
    traffic_share_pct: int = Field(60, ge=0, le=100, description="สัดส่วนระยะทางที่วิ่งในเมือง/รถติด (%)")
    fuel_price: float = Field(41.5, gt=0, le=100, description="ราคาน้ำมันต่อลิตร (บาท)")


# ---------- รายการที่สนใจ (watchlist) ----------

class WatchlistCreate(BaseModel):
    car_id: str = Field(..., description="รหัสรุ่นรถที่ต้องการติดตาม")


# ---------- บริการหลังการขาย ----------

class ReviewCreate(BaseModel):
    car_id: str
    rating: int = Field(..., ge=1, le=5, description="คะแนน 1-5 ดาว")
    title: Annotated[Stripped, Field(min_length=2, max_length=80)]
    comment: Annotated[Stripped, Field(min_length=10, max_length=1000)]


class ServiceAppointmentCreate(BaseModel):
    car_id: str
    showroom_id: str = Field(..., description="สาขาที่มีศูนย์บริการ")
    date: str = Field(..., description="วันที่นัด รูปแบบ YYYY-MM-DD")
    time: str = Field(..., description="เวลานัด เช่น 08:30")
    service_type: str = Field(..., description="ดูรายการจาก GET /api/service/types")
    mileage_km: int = Field(..., ge=0, le=1_000_000, description="เลขไมล์ปัจจุบัน")
    note: Annotated[Stripped, Field(max_length=500)] = ""


class RedeemCreate(BaseModel):
    reward_id: str

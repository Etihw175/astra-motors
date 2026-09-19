# Pydantic schemas — รูปแบบข้อมูลรับ-ส่งผ่าน API (validate อัตโนมัติทุก endpoint)
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class TestDriveCreate(BaseModel):
    car_id: str
    showroom_id: str
    date: str = Field(..., description="วันที่นัด รูปแบบ YYYY-MM-DD")
    time: str = Field(..., description="เวลานัด เช่น 10:00")
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=9, max_length=15)
    has_license: bool = Field(..., description="ยืนยันว่ามีใบขับขี่")
    contact_message_only: bool = Field(False, description="ให้ติดต่อผ่านข้อความเท่านั้น ไม่รับสายโทรศัพท์")


class ReservationCreate(BaseModel):
    car_id: str
    color_id: str
    option_ids: list[str] = []
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=9, max_length=15)
    email: str = Field(..., min_length=5, max_length=100)
    payment_method: str = Field(..., description="promptpay หรือ card (จำลอง)")
    contact_message_only: bool = False


class DeliveryCreate(BaseModel):
    date: str = Field(..., description="วันนัดรับรถ รูปแบบ YYYY-MM-DD")


class LoanCreate(BaseModel):
    reservation_code: str
    plan_id: str
    down_payment: int = Field(..., ge=0)
    term_months: int
    name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=9, max_length=15)
    occupation: str
    monthly_income: int = Field(..., gt=0)
    documents: list[str] = Field(default=[], description="ชื่อไฟล์เอกสารที่แนบ (จำลอง)")
    consent_pdpa: bool = Field(..., description="ยินยอมให้ใช้ข้อมูลตาม PDPA")


# ---------- Authentication / User Management ----------
# Pydantic ตรวจความถูกต้องให้อัตโนมัติ ถ้าผิดเงื่อนไข FastAPI ตอบ 422 พร้อมบอกฟิลด์ที่ผิดเอง

class RegisterCreate(BaseModel):
    username: str = Field(..., min_length=4, max_length=20,
                          description="a-z, 0-9, _ และ . เท่านั้น")
    password: str = Field(..., min_length=8, max_length=72)
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=9, max_length=15)


class LoginCreate(BaseModel):
    username: str = Field(..., min_length=1, description="ใช้ username หรืออีเมลก็ได้")
    password: str = Field(..., min_length=1)


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=72)


class UserUpdate(BaseModel):
    """แก้ไขข้อมูล user — ส่งมาเฉพาะฟิลด์ที่ต้องการแก้ (ฟิลด์ที่ไม่ส่งมาจะไม่ถูกแตะ)"""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=9, max_length=15)
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

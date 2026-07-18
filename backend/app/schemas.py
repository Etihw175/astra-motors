# Pydantic schemas — รูปแบบข้อมูลรับ-ส่งผ่าน API (validate อัตโนมัติทุก endpoint)
from pydantic import BaseModel, Field
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

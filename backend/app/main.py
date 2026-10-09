# จุดเริ่มแอป: รวม API routers ทั้งหมด + serve ไฟล์ frontend (static) ในตัวเดียวกัน
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from .database import IS_SQLITE, engine, init_db
from .routers import (
    admin,
    after_sales,
    auth,
    bookings,
    cars,
    documents,
    finance,
    loans,
    notifications,
    payments,
    reviews,
    showrooms,
    simulation,
    users,
    watchlist,
)

app = FastAPI(
    title="ASTRA Motors API",
    description="ระบบจองทดลองขับและซื้อรถออนไลน์ (Online Test Drive & Car Purchase System) "
                "ครบ 7 ขั้นตอนของ User Journey: รับรู้ → ค้นหา → ดูรายละเอียด → จองทดลองขับ → "
                "ซื้อออนไลน์ → ติดตามสถานะ → หลังการขาย — ข้อมูลทั้งหมดเก็บในฐานข้อมูล (PostgreSQL/SQLite)",
    version="0.3.0",
)

# สร้างตาราง + seed แคตตาล็อกและบัญชีตัวอย่าง (admin / somchai / nattaya)
init_db()


# ---------- security headers ----------
# ใส่ให้ทุก response (ทั้ง /api/* และไฟล์ static) ด้วย middleware ตัวเดียว
# จะได้ไม่ต้องไปจำใส่ทีละ endpoint แล้วลืมบางเส้น
#
# ไม่ใส่ Content-Security-Policy ไว้ตรงนี้โดยเจตนา:
#   หน้าเว็บโหลด <model-viewer> จาก CDN และฟอนต์จาก Google Fonts รวมทั้งมี inline style/script อยู่
#   CSP ที่เขียนหลวม ๆ ให้ของพวกนี้ผ่าน (unsafe-inline + wildcard CDN) แทบไม่กันอะไรเลย
#   ส่วน CSP ที่เข้มจริงต้องรื้อ inline ทั้งเว็บไปใช้ nonce ก่อน ซึ่งเป็นงานฝั่ง frontend
#   -> ปล่อยว่างไว้ดีกว่าใส่แบบหลอกตัวเอง และต้องทดสอบทุกหน้าใหม่หมดถ้าจะเพิ่มทีหลัง
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",      # ห้ามเบราว์เซอร์เดา MIME type เอง (กัน XSS จากไฟล์อัปโหลด)
    "X-Frame-Options": "DENY",                # ห้ามเอาเว็บไปฝังใน iframe (กัน clickjacking)
    "Referrer-Policy": "same-origin",         # ไม่ส่ง URL ของเราติดไปกับคำขอข้ามโดเมน
}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    return response


# ---------- ข้อผิดพลาดจากข้อมูลที่ส่งเข้ามา ----------
# ชื่อฟิลด์ภาษาไทย: ข้อความ 422 ของ Pydantic เป็นภาษาอังกฤษล้วน ลูกค้าอ่านไม่เข้าใจ
FIELD_LABELS = {
    "username": "ชื่อผู้ใช้", "password": "รหัสผ่าน", "current_password": "รหัสผ่านเดิม",
    "new_password": "รหัสผ่านใหม่", "full_name": "ชื่อ-นามสกุล", "email": "อีเมล",
    "phone": "เบอร์โทรศัพท์", "name": "ชื่อผู้ติดต่อ", "car_id": "รุ่นรถ", "color_id": "สี",
    "option_ids": "ออปชัน", "showroom_id": "สาขา", "date": "วันที่", "time": "เวลา",
    "rating": "คะแนน", "title": "หัวข้อ", "comment": "ความคิดเห็น", "note": "หมายเหตุ",
    "mileage_km": "เลขไมล์", "service_type": "ประเภทบริการ", "payment_method": "ช่องทางชำระเงิน",
    "method": "ช่องทางชำระเงิน", "card_last4": "เลข 4 ตัวท้ายบัตร", "down_payment": "เงินดาวน์",
    "term_months": "จำนวนงวด", "occupation": "อาชีพ", "monthly_income": "รายได้ต่อเดือน",
    "plan_id": "แผนสินเชื่อ", "reservation_code": "รหัสใบจอง", "consent_pdpa": "การยินยอม PDPA",
    "per_page": "จำนวนต่อหน้า", "page": "หน้า", "limit": "จำนวนรายการ", "role": "สิทธิ์การใช้งาน",
    "reward_id": "ของรางวัล", "has_license": "การยืนยันใบขับขี่",
}


def _field_label(location: tuple) -> str:
    """ชื่อฟิลด์ที่ผิด (ข้าม "body"/"query" ตัวแรกที่ Pydantic ใส่มา)"""
    parts = [str(p) for p in location if p not in ("body", "query", "path", "header")]
    name = parts[-1] if parts else ""
    return FIELD_LABELS.get(name, name or "ข้อมูลที่ส่งมา")


def _thai_reason(error: dict) -> str:
    """แปลงชนิดความผิดของ Pydantic เป็นประโยคไทยสั้น ๆ"""
    kind = error.get("type", "")
    ctx = error.get("ctx") or {}
    if kind == "missing":
        return "กรุณากรอกข้อมูลนี้"
    if kind.endswith("too_short"):
        least = ctx.get("min_length", ctx.get("actual_length"))
        return f"ต้องมีความยาวอย่างน้อย {least} ตัวอักษร" if least else "ข้อมูลสั้นเกินไป"
    if kind.endswith("too_long"):
        most = ctx.get("max_length")
        return f"ความยาวต้องไม่เกิน {most} ตัวอักษร" if most else "ข้อมูลยาวเกินไป"
    if kind in ("greater_than", "greater_than_equal"):
        return f"ต้องมีค่ามากกว่าหรือเท่ากับ {ctx.get('gt', ctx.get('ge', ''))}"
    if kind in ("less_than", "less_than_equal"):
        return f"ต้องมีค่าไม่เกิน {ctx.get('lt', ctx.get('le', ''))}"
    if kind.startswith("value_error") and ctx.get("error"):
        return str(ctx["error"])
    if "email" in kind:
        return "รูปแบบอีเมลไม่ถูกต้อง"
    if kind == "string_pattern_mismatch":
        return "รูปแบบข้อมูลไม่ถูกต้อง"
    if kind in ("int_parsing", "float_parsing", "int_type", "float_type"):
        return "ต้องเป็นตัวเลข"
    if kind in ("bool_parsing", "bool_type"):
        return "ต้องเป็น true หรือ false"
    if kind in ("json_invalid", "value_error.jsondecode"):
        return "ข้อมูลที่ส่งมาไม่ใช่ JSON ที่ถูกต้อง"
    return str(error.get("msg", "ข้อมูลไม่ถูกต้อง"))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """ตอบ 422 เป็นภาษาไทย พร้อมรายการฟิลด์ที่ผิดแบบที่โปรแกรมอ่านต่อได้

    ทำไมต้องเขียนเอง 2 เหตุผล:
      1) ข้อความมาตรฐานเป็นภาษาอังกฤษ ("Field required") ลูกค้าไทยอ่านไม่รู้เรื่อง
      2) ตัว handler เดิมสะท้อน "input" ดิบกลับไปด้วย ถ้า body มี UTF-8 เสีย
         (เช่น surrogate \\xed\\xa0\\x80) จะ encode response ไม่ได้ -> 500 Internal Server Error
         ที่นี่จึงไม่ส่ง input กลับเลย: ข้อมูลเสียกลายเป็น 422 ตามปกติ ไม่ใช่ 500
    detail ยังเป็น "ข้อความ" เหมือน HTTPException ทุกตัว หน้าเว็บที่โชว์ detail อยู่แล้วจึงไม่ต้องแก้
    """
    fields = []
    for error in exc.errors():
        location = tuple(error.get("loc", ()))
        fields.append({
            "field": ".".join(str(p) for p in location[1:]) or ".".join(str(p) for p in location),
            "label": _field_label(location),
            "message": _thai_reason(error),
        })
    summary = "; ".join(f"{f['label']}: {f['message']}" for f in fields) or "ข้อมูลที่ส่งมาไม่ถูกต้อง"
    return JSONResponse(status_code=422, content={"detail": summary, "fields": fields})


@app.exception_handler(UnicodeError)
async def unicode_error_handler(request: Request, exc: UnicodeError):
    """body ที่ถอดรหัสเป็นข้อความไม่ได้ ถือเป็นคำขอเสีย (400) ไม่ใช่เซิร์ฟเวอร์พัง (500)"""
    return JSONResponse(status_code=400, content={"detail": "ข้อมูลที่ส่งมาไม่ใช่ข้อความ UTF-8 ที่ถูกต้อง"})

# เรียงตาม service ในแผนภาพสถาปัตยกรรม (docs/architecture/)
for module in (
    auth, users,                    # Identity service
    cars, showrooms, finance,       # Catalog service
    watchlist,                      # Catalog service (รายการที่สนใจ — ต้องล็อกอิน)
    bookings,                       # Booking + Order service
    payments,                       # Payment service (จ่ายเงินจองก่อนออกใบจอง)
    loans, documents,               # Finance service
    notifications,                  # Notification service
    reviews, after_sales,           # After-sales + Loyalty service
    simulation,                     # Simulation service
    admin,                          # หลังบ้านพนักงานโชว์รูม (มุมมองข้ามทุก service)
):
    app.include_router(module.router)


@app.get("/api/health")
def health():
    """ใช้ทั้ง healthcheck ของ Docker และเช็คว่าเชื่อมฐานข้อมูลได้จริง"""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "sqlite" if IS_SQLITE else "postgresql"}


# หาโฟลเดอร์ frontend: ใน Docker คือ /app/frontend, รันตรงจากเครื่องคือ <repo>/frontend
_here = Path(__file__).resolve()
_candidates = [_here.parents[1] / "frontend", _here.parents[2] / "frontend"]
FRONTEND_DIR = next((p for p in _candidates if p.exists()), _candidates[0])

# mount ไว้ท้ายสุดเสมอ เพื่อให้เส้นทาง /api/* ทำงานก่อน
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

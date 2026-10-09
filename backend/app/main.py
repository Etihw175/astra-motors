# จุดเริ่มแอป: รวม API routers ทั้งหมด + serve ไฟล์ frontend (static) ในตัวเดียวกัน
from pathlib import Path

from fastapi import FastAPI
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
    reviews,
    showrooms,
    simulation,
    users,
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

# เรียงตาม service ในแผนภาพสถาปัตยกรรม (docs/architecture/)
for module in (
    auth, users,                    # Identity service
    cars, showrooms, finance,       # Catalog service
    bookings,                       # Booking + Order service
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

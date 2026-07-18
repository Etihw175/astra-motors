# จุดเริ่มแอป: รวม API routers ทั้งหมด + serve ไฟล์ frontend (static) ในตัวเดียวกัน
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import bookings, cars, finance, loans, showrooms

app = FastAPI(
    title="ASTRA Motors API",
    description="API จำลองสำหรับระบบเปรียบเทียบรถ จองทดลองขับ และจอง/ขอสินเชื่อออนไลน์ "
                "(User Journey #15 ยานยนต์)",
    version="0.1.0",
)

app.include_router(cars.router)
app.include_router(showrooms.router)
app.include_router(finance.router)
app.include_router(bookings.router)
app.include_router(loans.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# หาโฟลเดอร์ frontend: ใน Docker คือ /app/frontend, รันตรงจากเครื่องคือ <repo>/frontend
_here = Path(__file__).resolve()
_candidates = [_here.parents[1] / "frontend", _here.parents[2] / "frontend"]
FRONTEND_DIR = next((p for p in _candidates if p.exists()), _candidates[0])

# mount ไว้ท้ายสุดเสมอ เพื่อให้เส้นทาง /api/* ทำงานก่อน
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

# ASTRA Motors — จองทดลองขับ & ซื้อรถออนไลน์

เว็บแอปจาก **User Journey #15 (ยานยนต์)**: เปรียบเทียบสเปค/ราคารถ → คำนวณไฟแนนซ์ → จองทดลองขับ →
วางเงินจองออนไลน์ → ยื่นขอสินเชื่อ → ติดตามผลอนุมัติ → นัดรับรถ

> ทุก endpoint คืนค่า **mock data** (เก็บใน memory) ยังไม่เชื่อมฐานข้อมูลจริง
> การชำระเงินเป็นการจำลองทั้งหมด — รายชื่อรถเป็นรถจริงที่มีชื่อเสียง (GT-R, 911, Huracán, 488)
> เพื่อการศึกษาและเพื่อให้หาโมเดล 3D ได้ง่าย ราคา/สเปค/โปรโมชั่นเป็นการจำลอง ไม่ผูกกับแบรนด์หรือ
> ตัวแทนจำหน่ายจริง (journey ต้นทางเป็น SUV ครอบครัว — เปลี่ยนเป็นซูเปอร์คาร์โดยโครงสร้าง
> ทุกขั้นตอนของ journey ยังครบเหมือนเดิม)

- **URL ที่ deploy แล้ว:** _(เติมหลัง deploy สำเร็จ)_
- **Stack:** FastAPI (Python) + HTML/CSS/JavaScript ธรรมดา + Docker Compose

## วิธีรัน

```bash
docker compose up
```

- เว็บ: http://localhost:8000
- Swagger UI (ทดสอบ API): http://localhost:8000/docs

ปิดด้วย `docker compose down` — แก้ไฟล์ใน `backend/app/` หรือ `frontend/` เห็นผลทันที ไม่ต้อง build ใหม่

รันแบบไม่ใช้ Docker (ต้องมี Python 3.12+):

```bash
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
```

## แผนที่ User Journey → หน้าจอ

| ขั้นตอน | หน้าจอ | ไฟล์ |
|---|---|---|
| 1. เปรียบเทียบรุ่นรถ | ตารางเทียบสเปคเคียงข้างกัน สูงสุด 3 รุ่น | `frontend/pages/compare.html` |
| 2. รายละเอียดรุ่น | เลือกสี/ออปชัน ราคาอัปเดต real-time | `frontend/pages/model.html` |
| 3. เครื่องคำนวณไฟแนนซ์ | เงินดาวน์/งวดผ่อน เทียบหลายสถาบัน | `frontend/pages/finance.html` |
| 4. จองทดลองขับ | เลือกโชว์รูม + วัน-เวลาว่างจริงจากระบบ | `frontend/pages/test-drive.html` |
| 6. จองซื้อออนไลน์ | วางเงินจอง (จำลอง) ล็อกราคา ออกใบจอง | `frontend/pages/reserve.html` |
| 7. ยื่นขอสินเชื่อ | ฟอร์ม + แนบเอกสาร (จำลอง) | `frontend/pages/loan.html` |
| 5, 8. ติดตามสถานะ/นัดรับรถ | status stepper + ผลอนุมัติ + นัดรับรถ | `frontend/pages/status.html` |

Edge cases ที่รองรับแล้ว: สินเชื่อไม่ผ่าน (เสนอทางเลือก), สี/รุ่นรอผลิต (แจ้งจำนวนสัปดาห์),
ยกเลิกใบจอง+เงื่อนไขคืนเงิน, โปรโมชั่นหมดอายุ, ล็อกราคา ณ วันออกใบจอง, บล็อกวันจองย้อนหลัง

## โครงสร้างโปรเจกต์

```
backend/
  app/
    main.py            # จุดเริ่มแอป + serve frontend เป็น static files
    data.py            # mock data (รถ, โชว์รูม, แผนสินเชื่อ)
    schemas.py         # Pydantic validate ข้อมูลเข้า
    routers/           # แยก endpoint ตามหมวดของ journey
  requirements.txt
  Dockerfile           # build context = root ของ repo (สำคัญตอน deploy)
frontend/
  index.html
  pages/               # หน้าจอ .html ตามขั้นตอนใน journey
  css/style.css        # design tokens + component styles
  js/                  # api.js (fetch), ui.js (ส่วนกลาง), แยกไฟล์ต่อหน้า
docker-compose.yml
```

## API หลัก (ดูทั้งหมด + ทดสอบได้ที่ `/docs`)

- `GET /api/cars`, `GET /api/cars/{id}` — ข้อมูลรุ่นรถ
- `GET /api/showrooms`, `GET /api/showrooms/{id}/slots?date=` — โชว์รูม + คิวว่าง
- `GET /api/finance/plans` — แผนสินเชื่อ
- `POST /api/testdrives` — จองทดลองขับ
- `POST /api/reservations`, `POST /api/reservations/{code}/cancel`, `POST /api/reservations/{code}/delivery`
- `POST /api/loans`, `GET /api/loans/{id}` — ยื่น/ติดตามสินเชื่อ (ผลออกใน ~20 วินาที)

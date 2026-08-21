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
| ทุกขั้นตอน — บัญชีสมาชิก | สมัคร/เข้าสู่ระบบ | `frontend/pages/register.html`, `frontend/pages/login.html` |
| ทุกขั้นตอน — บัญชีสมาชิก | แก้ข้อมูลส่วนตัว เปลี่ยนรหัสผ่าน และหน้าจัดการผู้ใช้ของ admin | `frontend/pages/profile.html` |

Edge cases ที่รองรับแล้ว: สินเชื่อไม่ผ่าน (เสนอทางเลือก), สี/รุ่นรอผลิต (แจ้งจำนวนสัปดาห์),
ยกเลิกใบจอง+เงื่อนไขคืนเงิน, โปรโมชั่นหมดอายุ, ล็อกราคา ณ วันออกใบจอง, บล็อกวันจองย้อนหลัง

## โครงสร้างโปรเจกต์

```
backend/
  app/
    main.py            # จุดเริ่มแอป + serve frontend เป็น static files
    data.py            # mock data (รถ, โชว์รูม, แผนสินเชื่อ, ผู้ใช้)
    schemas.py         # Pydantic validate ข้อมูลเข้า
    security.py        # แฮชรหัสผ่าน (PBKDF2) + จัดการ token + ตรวจสิทธิ์
    routers/           # แยก endpoint ตามหมวดของ journey (auth.py, users.py, cars.py, ...)
  tests/               # pytest ครอบคลุม auth + สิทธิ์ + edge case
  requirements.txt
  requirements-dev.txt # แพ็กเกจสำหรับรันเทสต์เท่านั้น
  Dockerfile           # build context = root ของ repo (สำคัญตอน deploy)
frontend/
  index.html
  pages/               # หน้าจอ .html ตามขั้นตอนใน journey
  css/style.css        # design tokens + component styles
  js/                  # api.js (fetch), ui.js (ส่วนกลาง), แยกไฟล์ต่อหน้า
docs/
  api-spec.md          # รายการ endpoint ทั้งหมด + เงื่อนไข/สถานะที่ตอบกลับ
  presentation.md      # สคริปต์นำเสนอ 5 นาที + ลำดับการเดโม
docker-compose.yml     # web (FastAPI) + db (PostgreSQL)
```

## API หลัก (ดูทั้งหมด + ทดสอบได้ที่ `/docs` — รายละเอียดเต็มใน [`docs/api-spec.md`](docs/api-spec.md))

### ระบบสมาชิก (Authentication)

- `POST /api/register` — สมัครสมาชิก (คืน token ให้เลย)
- `POST /api/login` — เข้าสู่ระบบด้วย username หรืออีเมล
- `POST /api/logout` — ออกจากระบบ (ยกเลิก token ปัจจุบัน)
- `POST /api/change-password` — เปลี่ยนรหัสผ่าน (สำเร็จแล้วเตะทุกอุปกรณ์ออก)

### จัดการข้อมูลผู้ใช้ (User Management)

- `GET /api/me` — ดึงข้อมูลตัวเอง
- `GET /api/users` — ดึงข้อมูล user ทั้งหมดแบบแบ่งหน้า (`?page=&per_page=&q=&role=`) — เฉพาะ admin
- `GET /api/users/{id}` — ดึงข้อมูล user รายคน (เจ้าของบัญชีหรือ admin)
- `PUT /api/users/{id}` — แก้ไขข้อมูล user (`role`/`is_active` เฉพาะ admin)
- `DELETE /api/users/{id}` — ลบ user (เฉพาะ admin และลบตัวเองไม่ได้)
- `GET /api/check-username/{name}` — ตรวจสอบ username ว่างไหม (ไม่ต้องล็อกอิน)

การยืนยันตัวตนใช้ **Bearer token**: ล็อกอินแล้วแนบ `Authorization: Bearer <token>` ไปกับทุก request
(ใน Swagger UI กดปุ่ม **Authorize** แล้ววาง token ครั้งเดียว) — รหัสผ่านเก็บเป็น hash
PBKDF2-HMAC-SHA256 120,000 รอบ พร้อม salt รายบัญชี ไม่เก็บ plain text

บัญชีตัวอย่างที่ระบบสร้างให้ตอนเริ่มทำงาน: `admin / admin1234` (ผู้ดูแลระบบ),
`somchai / somchai123` และ `nattaya / nattaya123` (สมาชิกทั่วไป)

### API ตาม journey

- `GET /api/cars`, `GET /api/cars/{id}` — ข้อมูลรุ่นรถ
- `GET /api/showrooms`, `GET /api/showrooms/{id}/slots?date=` — โชว์รูม + คิวว่าง
- `GET /api/finance/plans` — แผนสินเชื่อ
- `POST /api/testdrives` — จองทดลองขับ
- `POST /api/reservations`, `POST /api/reservations/{code}/cancel`, `POST /api/reservations/{code}/delivery`
- `POST /api/loans`, `GET /api/loans/{id}` — ยื่น/ติดตามสินเชื่อ (ผลออกใน ~20 วินาที)

## การทดสอบ

```bash
pip install -r backend/requirements-dev.txt
cd backend && pytest -q      # 15 เคส: สมัคร/ล็อกอิน/สิทธิ์/pagination/edge case
```

เทสต์ครอบคลุมทั้ง happy path และกรณีที่ต้องถูกปฏิเสธ เช่น ผู้ใช้ทั่วไปยกระดับตัวเองเป็น admin,
ลบบัญชีของตัวเอง, ใช้ token เดิมหลังเปลี่ยนรหัสผ่าน และบัญชีที่ถูกระงับล็อกอินไม่ได้

# ASTRA Motors — จองทดลองขับ & ซื้อรถออนไลน์

เว็บแอปจาก User Journey **ระบบจองทดลองขับและซื้อรถออนไลน์ (Online Test Drive & Car Purchase System)**
ครบ 7 ขั้นตอน: รับรู้ → ค้นหารถ → ดูรายละเอียด → จองทดลองขับ → ซื้อรถออนไลน์ → ติดตามสถานะ → หลังการขาย

> ข้อมูลทั้งหมดเก็บใน **ฐานข้อมูลจริง** (PostgreSQL ใน Docker / SQLite เมื่อรันในเครื่อง) ผ่าน SQLModel
> การชำระเงิน การพิจารณาสินเชื่อ และอีเมล/SMS เป็นการจำลอง — รายชื่อรถเป็นรถจริงที่มีชื่อเสียง (GT-R, 911, Huracán, 488)
> เพื่อการศึกษาและเพื่อให้หาโมเดล 3D ได้ง่าย ราคา/สเปค/โปรโมชั่นเป็นการจำลอง ไม่ผูกกับแบรนด์หรือตัวแทนจำหน่ายจริง

- **URL ที่ deploy แล้ว:** _(เติมหลัง deploy สำเร็จ)_
- **Stack:** FastAPI (Python) + HTML/CSS/JavaScript ธรรมดา + PostgreSQL (SQLModel) + Docker Compose
- **สถาปัตยกรรม:** [Microservices architecture + Technology stack + ER diagram](docs/ARCHITECTURE.md)
- **ความคืบหน้า:** [รายงาน integration + ประเมินตนเอง](docs/PROGRESS.md)

![Microservices architecture](docs/architecture/microservices-architecture.png)

## วิธีรัน

```bash
docker compose up --build
```

- เว็บ: http://localhost:8000
- Swagger UI (ทดสอบ API): http://localhost:8000/docs
- สถานะระบบ + ฐานข้อมูล: http://localhost:8000/api/health

ปิดด้วย `docker compose down` (ข้อมูลใน PostgreSQL ยังอยู่ใน volume `db_data`) —
แก้ไฟล์ใน `backend/app/` หรือ `frontend/` เห็นผลทันที ไม่ต้อง build ใหม่

รันแบบไม่ใช้ Docker (ต้องมี Python 3.12+) — ระบบจะใช้ SQLite ไฟล์ `backend/astra.db` ให้อัตโนมัติ:

```bash
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload
```

> ตารางถูกสร้างอัตโนมัติตอนเริ่มระบบ ถ้าแก้โครงสร้างตารางใน `models.py` ให้ลบ `backend/astra.db`
> (หรือ `docker compose down -v`) แล้วรันใหม่

## แผนที่ User Journey → หน้าจอ

รายละเอียด pain point / opportunity / API ของแต่ละขั้นอยู่ใน [`docs/user-journey.md`](docs/user-journey.md)

| ขั้นตอน | หน้าจอ | ไฟล์ |
|---|---|---|
| 1. รับรู้ | โปรโมชั่นที่ยังใช้ได้ + รีวิวล่าสุดจากสมาชิก | `frontend/index.html` |
| 2. ค้นหารถ | ค้นหา + กรองยี่ห้อ/ระบบขับเคลื่อน/งบ + เรียงลำดับ | `frontend/index.html` |
| 3. ดูรายละเอียด | โมเดล 3D หมุน 360°, เลือกสี/ออปชัน, เทียบรุ่น, คำนวณไฟแนนซ์, จำลองถนนไทย, รีวิวรายรุ่น | `model.html`, `compare.html`, `finance.html`, `thai-road.html` |
| 4. จองทดลองขับ | เลือกโชว์รูม + คิวว่างเรียลไทม์จากการจองจริง | `frontend/pages/test-drive.html` |
| 5. ซื้อรถออนไลน์ | วางเงินจอง (จำลอง) ล็อกราคา + อัปโหลดเอกสาร + ยื่นสินเชื่อ | `reserve.html`, `loan.html` |
| 6. ติดตามสถานะ | การจองทั้งหมดของบัญชี + stepper + ผลสินเชื่อเรียลไทม์ + กระดิ่งแจ้งเตือน | `frontend/pages/status.html` |
| 7. หลังการขาย | คะแนนสะสม/แลกรางวัล, นัดเข้าศูนย์บริการ, รีวิว | `frontend/pages/after-sales.html` |
| ทุกขั้นตอน — บัญชีสมาชิก | สมัคร/เข้าสู่ระบบ/แก้ข้อมูล + หน้าจัดการผู้ใช้ของ admin | `register.html`, `login.html`, `profile.html` |

Edge cases ที่รองรับแล้ว: สินเชื่อไม่ผ่าน (คำนวณทางเลือก + ยื่นใหม่ได้), สี/รุ่นรอผลิต, ยกเลิกใบจอง+เงื่อนไขคืนเงิน,
โปรโมชั่นหมดอายุ, ล็อกราคา ณ วันออกใบจอง, บล็อกวันจองย้อนหลัง, จองคิวทดลองขับซ้อน, ยื่นสินเชื่อซ้อน,
นัดรับรถก่อนสินเชื่ออนุมัติ, ศูนย์บริการเต็ม, ไฟล์เอกสารปลอมนามสกุล, ปั๊มคะแนนด้วยการจอง-ยกเลิก

## โครงสร้างโปรเจกต์

```
backend/
  app/
    main.py            # จุดเริ่มแอป (API gateway) + serve frontend เป็น static files
    database.py        # เชื่อมฐานข้อมูลจาก DATABASE_URL (PostgreSQL / SQLite)
    models.py          # ตาราง SQLModel 13 ตาราง จัดกลุ่มตาม service
    crud.py            # ตัวช่วยอ่านข้อมูล + แปลง row เป็น JSON
    seed.py            # นำข้อมูลตั้งต้นจาก data.py ลงฐานข้อมูล
    data.py            # ข้อมูลตั้งต้น (รถ, โชว์รูม, แผนสินเชื่อ, บัญชีตัวอย่าง, ค่าคงที่)
    events.py          # event bus (publish / subscribe) ระหว่าง service
    schemas.py         # Pydantic validate ข้อมูลเข้า
    security.py        # แฮชรหัสผ่าน (PBKDF2) + session token + ตรวจสิทธิ์
    routers/           # 1 ไฟล์ต่อ service: auth, users, cars, showrooms, finance, bookings,
                       # loans, documents, notifications, reviews, after_sales, simulation
  tests/               # pytest 41 เคส: auth + สิทธิ์ + ครบ 7 ขั้นตอนของ journey
  requirements.txt
  requirements-dev.txt # แพ็กเกจสำหรับรันเทสต์เท่านั้น
  Dockerfile           # build context = root ของ repo (สำคัญตอน deploy)
frontend/
  index.html
  pages/               # หน้าจอ .html ตามขั้นตอนใน journey
  css/style.css        # design tokens + component styles
  js/                  # api.js (fetch), ui.js (ส่วนกลาง + กระดิ่งแจ้งเตือน), แยกไฟล์ต่อหน้า
docs/
  ARCHITECTURE.md      # Microservices architecture + Technology stack + ER diagram
  architecture/        # ไฟล์แผนภาพ .svg / .png
  user-journey.md      # journey → หน้าจอ → API
  PROGRESS.md          # ส่วนที่เสร็จ/ยังไม่เสร็จ + ประเมินตนเอง
docker-compose.yml     # web (FastAPI) + db (PostgreSQL 16)
```

## API หลัก (ดูทั้งหมด + ทดสอบได้ที่ `/docs`)

### ระบบสมาชิก (Identity service)

- `POST /api/register` — สมัครสมาชิก (คืน token ให้เลย)
- `POST /api/login` — เข้าสู่ระบบด้วย username หรืออีเมล
- `POST /api/logout` — ออกจากระบบ (ยกเลิก token ปัจจุบัน)
- `POST /api/change-password` — เปลี่ยนรหัสผ่าน (สำเร็จแล้วเตะทุกอุปกรณ์ออก)
- `GET /api/me` — ดึงข้อมูลตัวเอง
- `GET /api/users` — ดึงข้อมูล user ทั้งหมดแบบแบ่งหน้า (`?page=&per_page=&q=&role=`) — เฉพาะ admin
- `GET /api/users/{id}` / `PUT /api/users/{id}` / `DELETE /api/users/{id}` — ดู/แก้/ลบ (เจ้าของหรือ admin ตามสิทธิ์)
- `GET /api/check-username/{name}` — ตรวจสอบ username ว่างไหม (ไม่ต้องล็อกอิน)

การยืนยันตัวตนใช้ **Bearer token**: ล็อกอินแล้วแนบ `Authorization: Bearer <token>` ไปกับทุก request
(ใน Swagger UI กดปุ่ม **Authorize** แล้ววาง token ครั้งเดียว) — รหัสผ่านเก็บเป็น hash
PBKDF2-HMAC-SHA256 120,000 รอบ พร้อม salt รายบัญชี และฐานข้อมูลเก็บเฉพาะ SHA-256 ของ token

บัญชีตัวอย่างที่ระบบสร้างให้ตอนเริ่มทำงาน: `admin / admin1234` (ผู้ดูแลระบบ),
`somchai / somchai123` และ `nattaya / nattaya123` (สมาชิกทั่วไป)

### API ตาม journey

- `GET /api/cars?q=&brand=&drive=&min_price=&max_price=&sort=` · `GET /api/cars/facets` · `GET /api/cars/{id}` — ค้นหา/รายละเอียดรถ
- `GET /api/promotions` — โปรโมชั่นที่ยังไม่หมดอายุ
- `GET /api/showrooms`, `GET /api/showrooms/{id}/slots?date=` — โชว์รูม + คิวว่างเรียลไทม์
- `POST /api/testdrives`, `POST /api/testdrives/{code}/cancel` — จอง/ยกเลิกทดลองขับ (guest ได้)
- `GET /api/finance/plans` — แผนสินเชื่อ
- `POST /api/reservations`, `POST /api/reservations/{code}/cancel`, `POST /api/reservations/{code}/delivery` — ต้องล็อกอิน
- `POST /api/documents` — อัปโหลดเอกสาร PDF/JPG/PNG ≤ 5 MB
- `POST /api/loans`, `GET /api/loans/{id}` — ยื่น/ติดตามสินเชื่อ (ผลออกใน ~20 วินาที)
- `GET /api/me/bookings` — การจองทั้งหมดของบัญชี (ทดลองขับ + ใบจอง + สินเชื่อ + นัดศูนย์)
- `GET /api/notifications`, `GET /api/notifications/unread-count`, `POST /api/notifications/read-all` — แจ้งเตือน
- `GET/POST /api/reviews`, `GET /api/reviews/mine`, `DELETE /api/reviews/{id}` — รีวิว
- `GET /api/service/types`, `GET /api/service/slots`, `POST/GET /api/service/appointments` — นัดเข้าศูนย์บริการ
- `GET /api/loyalty`, `POST /api/loyalty/redeem` — คะแนนสะสม + แลกของรางวัล
- `POST /api/simulation`, `GET /api/simulation/conditions` — จำลองการใช้งานบนถนนไทย

## การทดสอบ

```bash
pip install -r backend/requirements-dev.txt
cd backend && pytest -q      # 41 เคส (ใช้ SQLite ชั่วคราว ไม่แตะข้อมูลจริง)
```

อยากรันกับ PostgreSQL: ตั้ง `TEST_DATABASE_URL=postgresql://user:pass@host:5432/ฐานข้อมูลว่าง` ก่อนรัน `pytest`

เทสต์ครอบคลุมทั้ง happy path และกรณีที่ต้องถูกปฏิเสธ เช่น ผู้ใช้ทั่วไปยกระดับตัวเองเป็น admin,
ดู/ยกเลิกใบจองของคนอื่น, จองคิวซ้อน, แนบเอกสารของคนอื่น, นัดรับรถก่อนสินเชื่ออนุมัติ และศูนย์บริการเต็ม

## การเปลี่ยนโครงสร้างฐานข้อมูล (migration)

โครงตารางคุมด้วย Alembic (`backend/alembic/`) รันทุกคำสั่งจากโฟลเดอร์ `backend/`:

```bash
cd backend
alembic revision --autogenerate -m "เพิ่มคอลัมน์ ..."   # หลังแก้ app/models.py
alembic upgrade head                                   # ลงโครงใหม่
alembic downgrade -1                                   # ถอยกลับ 1 ขั้นถ้าพลาด
```

ตอน deploy บน PostgreSQL แอปรัน `alembic upgrade head` ให้เองตอนสตาร์ต (ตั้ง `AUTO_MIGRATE=0`
ถ้าอยากรันเอง) ส่วนตอน dev/รันเทสต์ที่ใช้ SQLite ยังสร้างตารางด้วย `create_all()` ตามเดิม
รายละเอียดอยู่ใน `docs/DEPLOY.md`

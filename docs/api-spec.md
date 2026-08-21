# API Spec — ASTRA Motors

Base URL (รันในเครื่อง): `http://localhost:8000`
เอกสารทดสอบยิง API แบบ interactive: **`/docs`** (Swagger UI) และ **`/redoc`**

ทุก endpoint คืนค่าเป็น JSON และ validate ข้อมูลขาเข้าด้วย Pydantic
ถ้าข้อมูลผิดรูปแบบ FastAPI จะตอบ `422` พร้อมบอกฟิลด์ที่ผิดให้เองอัตโนมัติ

---

## 0. การยืนยันตัวตน (Bearer Token)

1. เรียก `POST /api/login` → ได้ `access_token`
2. แนบ token ไปกับทุก request ที่ต้องล็อกอิน:

```
Authorization: Bearer <access_token>
```

ใน Swagger UI กดปุ่ม **Authorize** มุมขวาบน แล้ววาง token ลงไปครั้งเดียว ใช้ได้ทุก endpoint

- token หมดอายุใน **8 ชั่วโมง**
- รหัสผ่านเก็บเป็น hash แบบ **PBKDF2-HMAC-SHA256 (120,000 รอบ + salt สุ่มรายบัญชี)** ไม่เก็บ plain text
- `logout`, เปลี่ยนรหัสผ่าน, ถูกระงับบัญชี หรือถูกลบบัญชี → token เดิมใช้ต่อไม่ได้ทันที

### บัญชีตัวอย่าง (สร้างอัตโนมัติตอนแอปเริ่มทำงาน)

| username | password | สิทธิ์ |
|---|---|---|
| `admin` | `admin1234` | admin — ดู/แก้/ลบผู้ใช้ทุกคนได้ |
| `somchai` | `somchai123` | customer |
| `nattaya` | `nattaya123` | customer |

---

## 1. Authentication (ล็อกอิน/สมัคร)

| Method | Path | ต้องล็อกอิน | คำอธิบาย |
|---|---|---|---|
| POST | `/api/register` | ❌ | สมัครสมาชิก (คืน token ให้เลย ไม่ต้องล็อกอินซ้ำ) |
| POST | `/api/login` | ❌ | เข้าสู่ระบบด้วย username **หรืออีเมล** |
| POST | `/api/logout` | ✅ | ออกจากระบบ (ยกเลิก token ปัจจุบัน) |
| POST | `/api/change-password` | ✅ | เปลี่ยนรหัสผ่านของตัวเอง |

### POST /api/register → `201 Created`

```json
{
  "username": "somsri",
  "password": "somsri1234",
  "full_name": "สมศรี มีสุข",
  "email": "somsri@example.com",
  "phone": "0812345678"
}
```

กติกา / error ที่รองรับ:

| กรณี | Status | ข้อความ |
|---|---|---|
| username ผิดรูปแบบ (ไม่ใช่ a-z 0-9 _ . หรือยาวไม่ถึง 4) | 400 | `username ใช้ได้เฉพาะ a-z, 0-9, _ และ . ความยาว 4-20 ตัวอักษร` |
| username ซ้ำ | 409 | `username นี้ถูกใช้แล้ว กรุณาเลือกชื่ออื่น` |
| อีเมลซ้ำ | 409 | `อีเมลนี้ถูกใช้สมัครไปแล้ว` |
| รหัสผ่านสั้น/ไม่มีตัวเลข | 400 | `รหัสผ่านต้องยาวอย่างน้อย 8 ตัวอักษร` / `...ต้องมีตัวเลขอย่างน้อย 1 ตัว` |
| รูปแบบอีเมลผิด, ฟิลด์ขาด | 422 | Pydantic ตอบให้อัตโนมัติ |

> ผู้สมัครเองได้สิทธิ์ `customer` เสมอ — ส่ง `"role": "admin"` มาก็ไม่มีผล (กันการยกระดับสิทธิ์ตัวเอง)

### POST /api/login → `200 OK`

```json
{ "username": "somchai", "password": "somchai123" }
```

ตอบกลับ:

```json
{
  "access_token": "R0Jk...",
  "token_type": "bearer",
  "expires_at": "2026-08-22T05:27:36",
  "user": { "id": 2, "username": "somchai", "role": "customer", "...": "..." }
}
```

| กรณี | Status |
|---|---|
| ไม่มี user นี้ **หรือ** รหัสผ่านผิด | 401 — ข้อความเดียวกันทั้งสองกรณี กันการเดาว่ามี username นี้อยู่จริงไหม (user enumeration) |
| บัญชีถูกระงับ (`is_active = false`) | 403 |

### POST /api/logout → `200 OK`

ต้องแนบ token — เรียกซ้ำด้วย token เดิมจะได้ `401` เพราะ token ถูกลบไปแล้ว

### POST /api/change-password → `200 OK`

```json
{ "current_password": "somchai123", "new_password": "somchai456" }
```

| กรณี | Status |
|---|---|
| รหัสผ่านเดิมไม่ถูกต้อง | 400 |
| รหัสใหม่ซ้ำรหัสเดิม / ไม่ผ่านเกณฑ์ | 400 |

สำเร็จแล้วระบบ **ยกเลิก session ทุกอุปกรณ์** ของบัญชีนั้น ต้องล็อกอินใหม่

---

## 2. User Management (จัดการข้อมูลผู้ใช้)

| Method | Path | สิทธิ์ที่ต้องมี | คำอธิบาย |
|---|---|---|---|
| GET | `/api/me` | ล็อกอิน | ดึงข้อมูลตัวเอง |
| GET | `/api/users` | **admin** | ดึงข้อมูล user ทั้งหมด (pagination) |
| GET | `/api/users/{id}` | เจ้าของบัญชี หรือ admin | ดึงข้อมูล user รายคน |
| PUT | `/api/users/{id}` | เจ้าของบัญชี หรือ admin | แก้ไขข้อมูล user |
| DELETE | `/api/users/{id}` | **admin** | ลบ user |
| GET | `/api/check-username/{name}` | ❌ ไม่ต้องล็อกอิน | ตรวจสอบ username ว่างไหม |

### GET /api/users — pagination + ค้นหา

Query parameters:

| ชื่อ | ค่าเริ่มต้น | เงื่อนไข |
|---|---|---|
| `page` | 1 | ≥ 1 |
| `per_page` | 10 | 1–100 (เกินตอบ 422) |
| `q` | – | ค้นหาจาก username / ชื่อ / อีเมล |
| `role` | – | `customer` หรือ `admin` |

ตัวอย่าง `GET /api/users?page=1&per_page=2`:

```json
{
  "items": [ { "id": 1, "username": "admin", "...": "..." } ],
  "page": 1,
  "per_page": 2,
  "total": 3,
  "total_pages": 2
}
```

### PUT /api/users/{id}

ส่งมาเฉพาะฟิลด์ที่ต้องการแก้ (partial update):

```json
{ "full_name": "สมชาย ใจดีมาก", "phone": "0855555555" }
```

| ฟิลด์ | ใครแก้ได้ |
|---|---|
| `full_name`, `email`, `phone` | เจ้าของบัญชี หรือ admin |
| `role`, `is_active` | **admin เท่านั้น** (ถ้าคนทั่วไปส่งมา → 403) |

| กรณี | Status |
|---|---|
| แก้ข้อมูลของคนอื่นโดยไม่ใช่ admin | 403 |
| ไม่พบ user | 404 |
| อีเมลชนกับบัญชีอื่น | 409 |
| ไม่ได้ส่งฟิลด์ใดมาเลย | 400 |
| ถอดสิทธิ์/ระงับ admin คนสุดท้ายในระบบ | 400 |

ระงับบัญชี (`is_active = false`) → token ที่ค้างอยู่ของบัญชีนั้นถูกยกเลิกทันที

### DELETE /api/users/{id} → `204 No Content`

| กรณี | Status |
|---|---|
| ไม่ใช่ admin | 403 |
| ลบบัญชีตัวเอง | 400 |
| ไม่พบ user | 404 |

### GET /api/check-username/{name}

ให้หน้าสมัครสมาชิกเรียกเช็คแบบ real-time ขณะพิมพ์ (ไม่ต้องล็อกอิน):

```json
{ "username": "admin", "valid": true, "available": false, "reason": "username นี้ถูกใช้แล้ว" }
```

---

## 3. API ตาม User Journey (ยานยนต์ #15)

| Method | Path | คำอธิบาย |
|---|---|---|
| GET | `/api/cars` · `/api/cars/{id}` | ข้อมูลรุ่นรถ สี ออปชัน โปรโมชั่น |
| GET | `/api/showrooms` · `/api/showrooms/{id}/slots?date=` | โชว์รูม + คิวทดลองขับที่ยังว่าง |
| GET | `/api/finance/plans` | แผนสินเชื่อของแต่ละสถาบัน |
| POST | `/api/testdrives` · GET `/api/testdrives/{code}` | จอง/ดูใบจองทดลองขับ |
| POST | `/api/reservations` · GET `/api/reservations/{code}` | วางเงินจองออนไลน์ + ล็อกราคา |
| POST | `/api/reservations/{code}/cancel` | ยกเลิกใบจอง + คำนวณเงินคืน |
| POST | `/api/reservations/{code}/delivery` | นัดวันรับรถ + รายการเอกสาร |
| POST | `/api/loans` · GET `/api/loans/{id}` | ยื่นสินเชื่อ + ติดตามผล (ผลออกใน ~20 วินาที) |
| GET | `/api/health` | health check (ใช้กับ Docker healthcheck และ Render) |

---

## 4. สรุป HTTP status ที่ใช้ในระบบนี้

| Status | ใช้เมื่อ |
|---|---|
| 200 | สำเร็จ มีข้อมูลตอบกลับ |
| 201 | สร้างข้อมูลใหม่สำเร็จ (register, จอง, ยื่นสินเชื่อ) |
| 204 | สำเร็จแต่ไม่มีเนื้อหาตอบกลับ (ลบ user) |
| 400 | ข้อมูลถูกรูปแบบแต่ผิดกติกาทางธุรกิจ (รหัสผ่านเดิมผิด, ลบบัญชีตัวเอง) |
| 401 | ยังไม่ล็อกอิน / token ผิดหรือหมดอายุ |
| 403 | ล็อกอินแล้วแต่ไม่มีสิทธิ์ (ไม่ใช่ admin, แตะข้อมูลคนอื่น, บัญชีถูกระงับ) |
| 404 | ไม่พบข้อมูล |
| 409 | ข้อมูลชนกัน (username/อีเมลซ้ำ, คิวทดลองขับถูกจองแล้ว) |
| 422 | ผิด schema — Pydantic ตอบให้อัตโนมัติพร้อมชื่อฟิลด์ |

---

## 5. ทดสอบ

```bash
# ทดสอบด้วย Swagger UI
docker compose up --build      # แล้วเปิด http://localhost:8000/docs

# ทดสอบอัตโนมัติ 15 เคส (happy path + สิทธิ์ + edge case)
pip install -r backend/requirements-dev.txt
cd backend && pytest -q
```

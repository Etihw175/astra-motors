# สถาปัตยกรรมระบบ ASTRA Motors

ระบบจองทดลองขับและซื้อรถออนไลน์ (Online Test Drive & Car Purchase System) — ครอบคลุม User Journey 7 ขั้นตอน
(ดูการจับคู่ขั้นตอน → หน้าจอ → API ใน [`user-journey.md`](user-journey.md))

## 1. Microservices Architecture

![Microservices architecture](architecture/microservices-architecture.png)

ไฟล์ต้นฉบับแบบเวกเตอร์: [`architecture/microservices-architecture.svg`](architecture/microservices-architecture.svg)

### ชั้นของระบบ (บนลงล่าง)

| ชั้น | หน้าที่ | อยู่ในโค้ดที่ |
|---|---|---|
| Clients | เว็บเบราว์เซอร์ของลูกค้า/ผู้ดูแลระบบ และ Swagger UI สำหรับนักพัฒนา | `frontend/` |
| API Gateway / Edge | จุดเข้าเดียวของทุก request: serve ไฟล์หน้าเว็บ, route `/api/*`, ตรวจ Bearer token, validate ข้อมูลด้วย Pydantic, สร้างเอกสาร OpenAPI | `backend/app/main.py`, `security.py` |
| Domain Services | 9 service แยกตามโดเมนธุรกิจ — แต่ละตัวเป็นเจ้าของ router และตารางของตัวเอง | `backend/app/routers/*.py` |
| Event Bus | service ต้นทางประกาศ event (เช่น `reservation.created`) ส่วน service ปลายทางสมัครรับเอง ไม่ต้องเรียกกันตรง ๆ | `backend/app/events.py` |
| Data | PostgreSQL 16 ผ่าน SQLModel (ORM) — SQLite ใช้ตอนรันในเครื่องและรันเทสต์ | `models.py`, `database.py`, `seed.py` |
| External (จำลอง) | Payment gateway, สถาบันการเงิน, Email/SMS | ตรรกะจำลองใน `bookings.py`, `loans.py` |

### รายการ service

| Service | Journey | Endpoint หลัก | ตารางที่เป็นเจ้าของ | Event |
|---|---|---|---|---|
| Identity | ทุกขั้นตอน | `/api/register` `/api/login` `/api/logout` `/api/me` `/api/users` | `users`, `auth_sessions` | — |
| Catalog | 1–3 | `/api/cars` (ค้นหา/กรอง/เรียง) `/api/cars/facets` `/api/promotions` `/api/showrooms` `/api/finance/plans` | `cars`, `showrooms`, `finance_plans` | — |
| Simulation | 3 | `POST /api/simulation` `/api/simulation/conditions` | — (stateless) | — |
| Booking | 4 | `/api/showrooms/{id}/slots` `/api/testdrives` `/api/testdrives/{code}/cancel` | `test_drives` | publish `testdrive.booked`, `testdrive.cancelled` |
| Order | 5–6 | `/api/reservations` `/{code}/cancel` `/{code}/delivery` `/api/me/bookings` | `reservations` | publish `reservation.created`, `reservation.cancelled`, `delivery.scheduled` |
| Finance | 5–6 | `/api/loans` `/api/loans/{id}` `/api/documents` | `loans`, `documents` | publish `loan.submitted`, `loan.decided` |
| After-sales | 7 | `/api/service/types` `/api/service/slots` `/api/service/appointments` `/api/reviews` | `service_appointments`, `reviews` | publish `service.booked`, `service.cancelled`, `review.posted`, `review.deleted` |
| Notification | 6 | `/api/notifications` `/unread-count` `/read-all` `/stream-ticket` `/stream` (SSE push) | `notifications` | subscribe ทุก event ที่ลูกค้าควรรู้ — ส่งถึงเบราว์เซอร์แบบ push (SSE) และมี poll เป็น fallback |
| Loyalty | 7 | `/api/loyalty` `/api/loyalty/redeem` | `point_transactions` | subscribe จอง/รีวิว/นัดศูนย์ (+คะแนน) และการยกเลิก (หักคืน), publish `points.redeemed` |

### ตัวอย่างการไหลของ event: ผลสินเชื่อออก → ลูกค้าเห็นแจ้งเตือน (SSE push, poll เป็น fallback)

```mermaid
sequenceDiagram
    participant B as Browser (status.html)
    participant G as API Gateway
    participant F as Finance Service
    participant E as Event Bus
    participant N as Notification Service
    participant DB as PostgreSQL

    B->>G: POST /api/notifications/stream-ticket (Bearer) — ขอตั๋วอายุ 30 วินาที ใช้ครั้งเดียว
    G-->>B: { ticket }
    B->>G: GET /api/notifications/stream?ticket=… (EventSource ค้างไว้)
    G-->>B: event: unread
    loop ทุก 2 วินาทีในสตรีม
        G->>F: settle_due_loans()
    end
    F->>DB: UPDATE loans SET status='approved'
    F->>E: publish loan.decided
    E->>N: handler(loan)
    N->>DB: INSERT notifications
    Note over F,DB: commit ครั้งเดียว — สำเร็จพร้อมกัน/ยกเลิกพร้อมกัน
    G-->>B: event: notification + event: unread (push ทันที ไม่ต้องรอรอบ poll)
    B->>B: toast "สินเชื่อได้รับการอนุมัติ" + ตัวเลขบนกระดิ่ง
    Note over B,G: สตรีมพัง/เบราว์เซอร์ไม่รองรับ EventSource → fallback ไป poll /unread-count ทุก 15 วินาที
```

### สถานะการแยก service (ตรงไปตรงมา)

ตอนนี้ deploy แบบ **modular monolith** — ทุก service รันใน process/container เดียว (`web`) คู่กับ `db`
แต่ขอบเขตของแต่ละ service ถูกแยกไว้แล้วครบ 3 ชั้น จึงแยกออกเป็น container ละ service ได้เมื่อจำเป็น:

1. **API แยก** — แต่ละ service มี router และ prefix ของตัวเอง → API Gateway (เช่น Nginx/Traefik) route ตาม prefix ได้ทันที
2. **ข้อมูลแยก** — แต่ละตารางมีเจ้าของ service เดียว (service อื่นอ่านผ่าน helper ใน `crud.py`)
3. **การสื่อสารแยก** — Notification/Loyalty ไม่ถูกเรียกตรง ๆ แต่รับ event → เปลี่ยน `events.py` เป็น RabbitMQ/Redis Streams
   ได้โดยไม่แก้ service ต้นทาง

## 2. Technology Stack

![Technology stack](architecture/tech-stack.png)

ไฟล์ต้นฉบับแบบเวกเตอร์: [`architecture/tech-stack.svg`](architecture/tech-stack.svg)

| ชั้น | เทคโนโลยี | ใช้ทำอะไร |
|---|---|---|
| Presentation | HTML5, CSS3, JavaScript (ES2020, ไม่มี framework/build step), `<model-viewer>` 3.5, Google Fonts | 13 หน้าตาม journey, โมเดล 3D หมุน 360°, เรียก API ด้วย `fetch()` |
| API / Application | FastAPI 0.115, Uvicorn 0.32, Pydantic v2, OpenAPI/Swagger UI, python-multipart | REST API + serve หน้าเว็บ, validate ข้อมูล, เอกสาร API ที่ `/docs`, อัปโหลดไฟล์ |
| Business logic | 9 service routers, Event bus, PBKDF2-SHA256 + Bearer token + RBAC | กติกาทางธุรกิจ, สิทธิ์การเข้าถึง, แจ้งเตือน/คะแนนแบบ event-driven |
| Data | SQLModel 0.0.22, SQLAlchemy 2.0, psycopg 3, PostgreSQL 16, SQLite | ORM + ฐานข้อมูลหลัก (Docker) + ฐานข้อมูลตอนพัฒนา/เทสต์ |
| DevOps | Docker, Docker Compose, Git/GitHub, pytest + httpx, Render/Railway | รันทั้งระบบด้วยคำสั่งเดียว, เทสต์อัตโนมัติ 41 เคส, deploy ด้วย Dockerfile เดิม |

## 3. โครงสร้างข้อมูล (ER diagram)

```mermaid
erDiagram
    users ||--o{ auth_sessions : "มี session"
    users ||--o{ test_drives : "จอง (guest ได้)"
    users ||--o{ reservations : "จองซื้อ"
    users ||--o{ loans : "ยื่น"
    users ||--o{ documents : "อัปโหลด"
    users ||--o{ reviews : "เขียน"
    users ||--o{ service_appointments : "นัด"
    users ||--o{ point_transactions : "สะสม/ใช้"
    users ||--o{ notifications : "ได้รับ"
    cars ||--o{ test_drives : ""
    cars ||--o{ reservations : ""
    cars ||--o{ reviews : ""
    cars ||--o{ service_appointments : ""
    showrooms ||--o{ test_drives : "คิวทดลองขับ"
    showrooms ||--o{ service_appointments : "ศูนย์บริการ"
    reservations ||--o{ loans : "ยื่นได้ใหม่ถ้าไม่ผ่าน"
    finance_plans ||--o{ loans : ""

    users {
        int id PK
        string username UK
        string email UK
        string password_hash
        string role
    }
    cars {
        string id PK
        string brand
        int price
        string drive_code
        json colors
        json options
        json promotion
    }
    test_drives {
        string code PK
        int user_id FK
        string car_id FK
        string showroom_id FK
        date date
        string time
        string status
    }
    reservations {
        string code PK
        int user_id FK
        string car_id FK
        int total_price
        date price_locked_until
        string status
        string loan_id
    }
    loans {
        string id PK
        string reservation_code FK
        string plan_id FK
        int monthly_payment
        string status
        json result
    }
    reviews {
        int id PK
        int user_id FK
        string car_id FK
        int rating
        bool verified
    }
    service_appointments {
        string code PK
        int user_id FK
        string showroom_id FK
        date date
        string time
        string status
    }
    point_transactions {
        int id PK
        int user_id FK
        int points
        string reason
    }
    notifications {
        int id PK
        int user_id FK
        string kind
        bool is_read
    }
```

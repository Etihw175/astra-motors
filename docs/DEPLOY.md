# คู่มือ Deploy ASTRA Motors ขึ้น URL สาธารณะ

> **หมายเหตุ:** ยังไม่ได้ deploy จริง เพราะยังไม่มีบัญชี Render ของนิสิต
> เอกสารนี้คือขั้นตอนที่ต้องทำ — ไฟล์ตั้งค่าทั้งหมด (`render.yaml`, `backend/Dockerfile`,
> `.dockerignore`) พร้อมอยู่ใน repo แล้ว

Repo: <https://github.com/Etihw175/astra-motors>

---

## วิธีที่ 1: Render ด้วย Blueprint (แนะนำ)

`render.yaml` ที่ root ของ repo บอก Render ไว้ครบแล้วว่าจะสร้างอะไร
(web service จาก Dockerfile + PostgreSQL + ผูก `DATABASE_URL` ให้กันเอง)
ไม่ต้องกรอก build command / start command ด้วยมือเลย

1. **Push โค้ดขึ้น GitHub ให้ครบ** — `render.yaml` ต้องอยู่บน branch `main`
   ```bash
   git add render.yaml .dockerignore .env.example backend/Dockerfile docs/DEPLOY.md
   git commit -m "chore: ไฟล์ตั้งค่า deploy สำหรับ Render"
   git push origin main
   ```
2. **สมัคร/ล็อกอิน Render** ที่ <https://dashboard.render.com> → เลือก **Sign in with GitHub**
   (ใช้บัญชี GitHub เดียวกับที่เป็นเจ้าของ repo จะง่ายที่สุด)
3. **New → Blueprint** (ปุ่ม **New +** มุมขวาบน)
4. **เชื่อม repo** — กด **Connect GitHub** / **Configure account** แล้วให้สิทธิ์เฉพาะ repo
   `astra-motors` → กลับมาเลือก repo นั้นในลิสต์ → **Connect**
5. Render อ่าน `render.yaml` แล้วแสดงว่าจะสร้าง 2 อย่าง: service `astra-motors`
   และฐานข้อมูล `astra-db` → ตั้ง **Blueprint Name** (อะไรก็ได้) → กด **Apply**
6. **รอ build** ~5-10 นาที (ครั้งแรกช้าเพราะต้อง pip install + copy โมเดล .glb)
   ดูความคืบหน้าที่แท็บ **Logs** ของ service — เสร็จแล้วสถานะเปลี่ยนเป็น **Live**
7. **เปิด URL** ที่ Render ให้มา — จะเป็น `https://astra-motors-xxxx.onrender.com`
   (ปุ่มลิงก์อยู่ใต้ชื่อ service) ควรเห็นหน้าแรกของเว็บ
8. **ตรวจว่าต่อฐานข้อมูลจริง** — เปิด `https://<URL>/api/health` ต้องได้
   ```json
   {"status":"ok","database":"postgresql"}
   ```
   ถ้าได้ `"database":"sqlite"` แปลว่า `DATABASE_URL` ไม่ถูกส่งเข้ามา (ดูหัวข้อแก้ปัญหา)
9. **เปิด API docs** — `https://<URL>/docs` (Swagger UI ของ FastAPI) ลองยิง API ได้จากหน้านี้

### ถ้าไม่อยากใช้ Blueprint (ตั้งเอง)

**New → Web Service** → เลือก repo → ตั้งค่า:
`Language/Runtime = Docker`, `Dockerfile Path = backend/Dockerfile`,
`Docker Build Context Directory = .`, `Health Check Path = /api/health`, `Instance Type = Free`
แล้วสร้าง **New → Postgres** แยก คัดลอก **Internal Database URL** มาใส่เป็น env var
`DATABASE_URL` ของ web service

---

## วิธีที่ 2: Railway (สั้น ๆ)

ใช้ `backend/Dockerfile` ตัวเดิม ไม่ต้องแก้อะไร

1. <https://railway.app> → **Login with GitHub** → **New Project** → **Deploy from GitHub repo**
2. เลือก repo → Settings ของ service: `Dockerfile Path = backend/Dockerfile`,
   `Root Directory = /` (context ต้องเป็น root)
3. ในโปรเจกต์เดียวกัน **+ New → Database → Add PostgreSQL**
4. ที่ service ของเว็บ → **Variables** → **Add Variable Reference** → เลือก
   `DATABASE_URL` ของ Postgres (Railway ใส่ `${{Postgres.DATABASE_URL}}` ให้)
5. **Settings → Networking → Generate Domain** เพื่อขอ URL สาธารณะ
   (Railway inject `PORT` ให้เอง — Dockerfile รองรับผ่าน `${PORT:-8000}` แล้ว)

---

## สิ่งที่ต้องรู้

- **ไม่ต้องรัน migration** — ตอนแอปเริ่ม `init_db()` ใน `backend/app/database.py`
  เรียก `SQLModel.metadata.create_all()` สร้างตารางที่ยังไม่มี แล้ว seed
  แคตตาล็อกรถ/โชว์รูม/แผนสินเชื่อ + บัญชีตัวอย่างให้เอง (ทำซ้ำได้ ไม่เกิดข้อมูลซ้ำ)
- **Free tier ของ Render จะ sleep** เมื่อไม่มีใครเข้าเกิน ~15 นาที คนเข้าครั้งถัดไป
  ต้องรอ cold start ~1 นาที (ตอนนำเสนอ ให้เปิดเว็บอุ่นเครื่องไว้ก่อน)
- **ข้อมูลไม่หายตอน sleep หรือ deploy ใหม่** เพราะอยู่ใน managed PostgreSQL
  คนละที่กับคอนเทนเนอร์ (ต่างจาก SQLite ที่อยู่ในดิสก์ของคอนเทนเนอร์ซึ่งหายทุกครั้งที่ deploy)
- **ฐานข้อมูล free ของ Render หมดอายุ 30 วัน** — Render จะส่งอีเมลเตือน ถ้าเลยกำหนด
  ต้องสร้างใหม่แล้ว deploy ซ้ำ (ข้อมูล seed สร้างกลับมาเองอยู่ดี)
- **ไม่มีความลับอยู่ใน repo** — `DATABASE_URL` มาจาก `fromDatabase` ใน `render.yaml`
  ส่วน `.env` ถูก `.gitignore` ไว้

## เช็กลิสต์หลัง deploy

- [ ] `/api/health` ตอบ `{"status":"ok","database":"postgresql"}`
- [ ] ล็อกอินด้วยบัญชีตัวอย่าง: `somchai` / `somchai123` (ลูกค้า) และ `admin` / `admin1234` (ผู้ดูแล)
- [ ] ค้นหารถ → เปิดหน้ารายละเอียด → โมเดล 3D หมุนได้ (ไฟล์ `.glb` โหลดขึ้น)
- [ ] จองทดลองขับสำเร็จ แล้วกลับมาดูรายการจองของตัวเองได้
- [ ] หน้าแจ้งเตือนมีข้อความใหม่โผล่หลังจอง
- [ ] เปิด `/docs` แล้วยิง API ได้จาก Swagger UI
- [ ] ลองเปิดเว็บใหม่หลังทิ้งไว้ 20 นาที — ข้อมูลที่จองไว้ยังอยู่ (พิสูจน์ว่าใช้ Postgres จริง)

## วิธีแก้ปัญหาที่เจอบ่อย

| อาการ | สาเหตุ | วิธีแก้ |
|---|---|---|
| Build fail: `requirements.txt not found` / `COPY failed` | context ผิด (ตั้งเป็น `backend/` แทน root) | ตั้ง Docker Build Context = `.` และ Dockerfile Path = `backend/Dockerfile` — `render.yaml` ตั้งถูกให้แล้ว |
| เปิด URL ได้ **502 Bad Gateway** แต่ log บอกว่าแอปรันอยู่ | uvicorn bind `127.0.0.1` ซึ่ง Render เข้าไม่ถึง | ต้องเป็น `--host 0.0.0.0 --port ${PORT:-8000}` และห้าม hardcode port ทับค่าที่ Render ส่งมา |
| `/api/health` บอก `"database":"sqlite"` | ลืมตั้ง `DATABASE_URL` (แอป fallback เป็น SQLite) ข้อมูลจะหายทุกครั้งที่ deploy | Dashboard → service → **Environment** ตรวจว่ามี `DATABASE_URL` ชี้ไป Postgres (ใช้ **Internal** URL ไม่ใช่ External) แล้ว **Manual Deploy** ใหม่ |
| Build นานมาก / timeout | โมเดล `.glb` 4 ไฟล์รวมกัน ~46 MB ต้องส่งขึ้น build server | `.dockerignore` ตัดโฟลเดอร์โมเดลสำรองออกแล้ว ถ้ายังช้าให้บีบไฟล์ `.glb` (gltf-pipeline / Draco) หรือย้ายไปโฮสต์เป็น static asset ภายนอก |
| หน้าแรกขึ้น แต่ `/api/*` ได้ 404 | static mount ทับเส้นทาง API | `app.mount("/")` ต้องอยู่บรรทัดท้ายสุดของ `backend/app/main.py` (ปัจจุบันถูกต้องแล้ว) |
| Deploy ค้างที่ `Health check failed` | `/api/health` เชื่อมฐานข้อมูลไม่ได้ จึงตอบ 500 | ดู Logs ของ service ว่าต่อ Postgres ไม่ได้เพราะอะไร มักเป็น `DATABASE_URL` ผิด region หรือฐานข้อมูลยัง provisioning ไม่เสร็จ |

---

## การเปลี่ยนโครงสร้างฐานข้อมูล (migration)

โครงตารางคุมด้วย **Alembic** แล้ว (`backend/alembic/`, revision ตั้งต้น `0001_initial` = 13 ตารางตาม
`app/models.py`) — ข้อความ "ไม่ต้องรัน migration" ในหัวข้อ *สิ่งที่ต้องรู้* ด้านบนใช้กับ SQLite ตอน dev
เท่านั้น บน PostgreSQL ใช้ migration แทน เพราะ `create_all()` เพิ่มได้แค่ตารางใหม่
แต่ **แก้คอลัมน์/ชนิดข้อมูลของตารางที่มีอยู่แล้วไม่ได้เลย** (เงียบ ๆ ไม่ error ด้วย)

รันทุกคำสั่งจากโฟลเดอร์ `backend/` (ที่เดียวกับ `alembic.ini`):

```bash
cd backend
alembic revision --autogenerate -m "เพิ่มคอลัมน์ ..."   # 1) แก้ app/models.py เสร็จแล้วสร้างไฟล์ migration
alembic upgrade head                                   # 2) ลงโครงใหม่กับฐานข้อมูลที่ DATABASE_URL ชี้อยู่
alembic downgrade -1                                   # 3) ถอยกลับ 1 ขั้นถ้าผลไม่เป็นอย่างที่คิด
```

> เปิดไฟล์ที่ `revision --autogenerate` สร้างให้อ่านก่อน **ทุกครั้ง** แล้ว commit ไฟล์นั้นเข้า repo
> ด้วย — ไม่ใช่ไฟล์ที่ generate ทิ้งได้

**บน Render ไม่ต้องรันเอง** — `init_db()` ใน `backend/app/database.py` เรียก `alembic upgrade head`
ให้อัตโนมัติตอนแอปสตาร์ต (ก่อน seed ข้อมูล) ทุกครั้งที่ deploy ใหม่ จึงไม่ต้องเข้า shell ของ Render
ตั้ง env var `AUTO_MIGRATE=0` ถ้าอยากปิดพฤติกรรมนี้แล้วรัน migration ด้วยมือเอง

หมายเหตุ: SQLite (dev ในเครื่อง + `pytest`) ยังใช้ `SQLModel.metadata.create_all()` ตามเดิม
เพราะเทสต์สร้างฐานข้อมูลใหม่ทุกครั้งอยู่แล้ว ส่วนเทสต์ `backend/tests/test_migrations.py`
คอยเช็กว่า migration ยัง upgrade/downgrade ผ่านและมี head เดียว

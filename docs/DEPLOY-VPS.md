# Deploy ขึ้น VPS ของตัวเอง (Ubuntu + Docker)

ใช้กับ server ที่ล็อกอิน SSH ได้และติดตั้งโปรแกรมเองได้ ถ้าใช้ Render ให้ดู `docs/DEPLOY.md` แทน

FileZilla ใช้ดูไฟล์หรือดึง backup กลับมาได้ แต่อย่าใช้ลากโค้ดขึ้นไป deploy
เว็บนี้ต้องมี Python กับ PostgreSQL รันอยู่บน server การอัปโหลดไฟล์เฉย ๆ ไม่ทำให้มันทำงาน
และไฟล์ที่ลากขึ้นมือจะไม่ตรงกับ repo ภายในไม่กี่รอบแก้ ใช้ `git pull` บน server แทน

## 0. สิ่งที่ต้องมี

- VPS Ubuntu 22.04 หรือใหม่กว่า แรมอย่างน้อย 1 GB ดิสก์ว่าง 5 GB
- สิทธิ์ `sudo`
- ถ้าจะทำ HTTPS ต้องมีโดเมนที่ชี้ A record มาที่ IP ของ server แล้ว

## 1. ต่อ SSH

```bash
ssh ubuntu@<IP ของ server>
```

ใน FileZilla ให้ตั้ง Protocol เป็น **SFTP** port 22 ถ้ายังใช้ FTP ธรรมดา port 21 อยู่
รหัสผ่านจะวิ่งเป็นข้อความธรรมดาและดักอ่านได้

## 2. ติดตั้ง Docker

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER
```

ออกจาก SSH แล้วต่อใหม่หนึ่งครั้ง กลุ่ม `docker` ถึงจะมีผล จากนั้นตรวจว่าได้จริง

```bash
docker run --rm hello-world
```

## 3. ดึงโค้ด

```bash
git clone https://github.com/Etihw175/astra-motors.git
cd astra-motors
```

## 4. สร้างไฟล์ .env

สุ่มรหัสผ่านฐานข้อมูลแทนการคิดเอง แล้วเขียนลงไฟล์เดียวกันทั้งสองที่ให้ตรงกัน

```bash
PGPASS=$(openssl rand -hex 24)
cat > .env <<EOF
POSTGRES_USER=astra
POSTGRES_PASSWORD=$PGPASS
POSTGRES_DB=astra
DATABASE_URL=postgresql://astra:$PGPASS@db:5432/astra
EOF
chmod 600 .env
```

`.env` อยู่ใน `.gitignore` แล้ว จะไม่ถูก push ขึ้น GitHub
host ใน `DATABASE_URL` ต้องเป็น `db` ซึ่งเป็นชื่อ service ของ Postgres ในเครือข่ายของ Compose
ไม่ใช่ `localhost`

## 5. รัน

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

ครั้งแรกใช้เวลาประมาณ 5 ถึง 10 นาที เพราะต้อง pip install และคัดลอกโมเดล 3D เข้า image
ตอนแอปสตาร์ต มันรัน `alembic upgrade head` แล้ว seed แคตตาล็อกรถกับบัญชีตัวอย่างให้เอง
ไม่ต้องรัน migration ด้วยมือ

ตรวจว่าขึ้นครบ

```bash
docker compose -f docker-compose.prod.yml ps
curl http://127.0.0.1:8000/api/health
```

ต้องได้ `{"status":"ok","database":"postgresql"}` ถ้าได้ `"sqlite"` แปลว่า `DATABASE_URL`
ไม่ถึงคอนเทนเนอร์ ให้ตรวจไฟล์ `.env` แล้ว `up -d` ใหม่

## 6. เปิดให้คนนอกเข้าถึงด้วย Caddy

`docker-compose.prod.yml` ผูกเว็บไว้ที่ `127.0.0.1:8000` ตั้งใจให้เข้าตรงจากภายนอกไม่ได้
ตัวรับ 80 กับ 443 คือ Caddy ซึ่งขอใบรับรอง HTTPS จาก Let's Encrypt ให้อัตโนมัติ

```bash
sudo apt install -y caddy
sudo tee /etc/caddy/Caddyfile >/dev/null <<'EOF'
astra.example.com {
    reverse_proxy 127.0.0.1:8000
}
EOF
sudo systemctl reload caddy
```

เปลี่ยน `astra.example.com` เป็นโดเมนจริง ถ้ายังไม่มีโดเมน ใช้ IP ไปก่อนได้แต่จะไม่มี HTTPS

```
:80 {
    reverse_proxy 127.0.0.1:8000
}
```

## 7. ปิดพอร์ตที่ไม่ได้ใช้

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

Postgres ไม่ต้องเปิดพอร์ตออกเน็ต `docker-compose.prod.yml` ไม่ได้ map พอร์ตของมันไว้อยู่แล้ว

## 8. เช็กลิสต์หลัง deploy

- [ ] `https://<โดเมน>/api/health` ตอบ `{"status":"ok","database":"postgresql"}`
- [ ] ล็อกอิน `somchai` / `somchai123` (ลูกค้า) และ `admin` / `admin1234` (ผู้ดูแล)
- [ ] **เปลี่ยนรหัสผ่านของทั้งสองบัญชีทันที** เพราะรหัส seed อยู่ในโค้ดสาธารณะ
- [ ] เปิดหน้ารายละเอียดรถ โมเดล 3D หมุนได้
- [ ] จองทดลองขับผ่าน แล้วหน้าแจ้งเตือนมีข้อความใหม่
- [ ] `https://<โดเมน>/docs` เปิด Swagger ได้
- [ ] restart server แล้วเว็บกลับมาเอง (`restart: always` ทำให้คอนเทนเนอร์ขึ้นตาม Docker)

## อัปเดตเวอร์ชันใหม่

```bash
cd ~/astra-motors
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

ข้อมูลอยู่ใน volume `db_data` ไม่หายตอน build ใหม่ migration รันเองตอนสตาร์ต

## สำรองฐานข้อมูล

```bash
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U astra astra > ~/astra-backup-$(date +%F).sql
```

ไฟล์ `.sql` ที่ได้ดึงกลับมาเก็บในเครื่องด้วย FileZilla ได้ กู้คืนด้วย

```bash
cat astra-backup-2026-10-31.sql | docker compose -f docker-compose.prod.yml exec -T db psql -U astra astra
```

ตั้งให้สำรองเองทุกคืนตีสอง

```bash
crontab -e
# เพิ่มบรรทัดนี้
0 2 * * * cd ~/astra-motors && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U astra astra > ~/backups/astra-$(date +\%F).sql
```

## ดู log กับแก้ปัญหา

```bash
docker compose -f docker-compose.prod.yml logs -f web     # log ของ FastAPI
docker compose -f docker-compose.prod.yml logs -f db      # log ของ Postgres
docker compose -f docker-compose.prod.yml restart web     # รีสตาร์ตเฉพาะเว็บ
```

| อาการ | สาเหตุ | วิธีแก้ |
|---|---|---|
| `curl` ได้ `Connection refused` | คอนเทนเนอร์ web ยังไม่ขึ้นหรือดับไปแล้ว | `docker compose -f docker-compose.prod.yml ps` ดูสถานะ แล้วอ่าน log ของ web |
| `/api/health` บอก `"database":"sqlite"` | `.env` ไม่มี `DATABASE_URL` หรือสะกดผิด | แก้ `.env` แล้ว `up -d` ใหม่ ข้อมูลที่เคยเขียนลง SQLite ในคอนเทนเนอร์จะหายไปด้วย |
| web ขึ้นแล้วดับวนไป | ต่อ Postgres ไม่ได้ มักเป็นรหัสผ่านใน `DATABASE_URL` ไม่ตรงกับ `POSTGRES_PASSWORD` | ถ้าเคย up ด้วยรหัสเก่ามาแล้ว ค่าเดิมฝังอยู่ใน volume ต้อง `docker compose -f docker-compose.prod.yml down -v` แล้วเริ่มใหม่ (ข้อมูลหายหมด) |
| build ค้างนานหรือดิสก์เต็ม | image เก่าค้างอยู่ | `docker image prune -f` |
| Caddy ขอใบรับรองไม่ผ่าน | โดเมนยังไม่ชี้มาที่ IP นี้ หรือพอร์ต 80 ถูกปิด | `dig +short <โดเมน>` ต้องได้ IP ของ server และ `sudo ufw status` ต้องเห็น 80 เปิดอยู่ |

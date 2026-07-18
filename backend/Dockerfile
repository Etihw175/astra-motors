# สำคัญ: build context ต้องเป็น root ของ repo (ไม่ใช่โฟลเดอร์ backend/)
# เพราะ image ต้อง COPY ทั้ง backend และ frontend เข้าไปด้วยกัน
# - Docker Compose ตั้ง context: . และ dockerfile: backend/Dockerfile ให้แล้ว
# - บน Render/Railway ให้ตั้ง Dockerfile path = backend/Dockerfile และ context = .
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY frontend ./frontend

EXPOSE 8000

# ${PORT} มีไว้รองรับ Render/Railway ที่กำหนด port ผ่าน env — รันในเครื่องจะใช้ 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

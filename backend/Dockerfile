# สำคัญ: build context ต้องเป็น root ของ repo (ไม่ใช่โฟลเดอร์ backend/)
# เพราะ image ต้อง COPY ทั้ง backend และ frontend เข้าไปด้วยกัน
# - Docker Compose ตั้ง context: . และ dockerfile: backend/Dockerfile ให้แล้ว
# - บน Render/Railway ให้ตั้ง Dockerfile path = backend/Dockerfile และ context = .
FROM python:3.12-slim

# PYTHONUNBUFFERED: log โผล่ใน Render Logs ทันที ไม่ค้างใน buffer เวลาแอปพัง
# PYTHONDONTWRITEBYTECODE: ไม่ต้องเขียน .pyc ลง image (เล็กลง และ user ที่ไม่ใช่ root เขียนไม่ได้อยู่ดี)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ติดตั้ง dependency แยกเป็นเลเยอร์ของตัวเอง — แก้โค้ดแล้ว build ใหม่ไม่ต้อง pip install ซ้ำ
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY frontend ./frontend

# รันด้วย user ธรรมดา ไม่ใช่ root — ถ้าแอปถูกเจาะ ผู้บุกรุกก็แก้ไฟล์ใน container ไม่ได้
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# ${PORT} มีไว้รองรับ Render/Railway ที่กำหนด port ผ่าน env — รันในเครื่องจะใช้ 8000
# host 0.0.0.0 ห้ามเปลี่ยนเป็น 127.0.0.1 ไม่งั้น Render เข้าไม่ถึงคอนเทนเนอร์ (502)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

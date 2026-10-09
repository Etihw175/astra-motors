# ตัวจำกัดอัตราการเรียก API (rate limiter) แบบนับในหน่วยความจำของ process
#
# ทำไมนับในหน่วยความจำได้ในโปรเจกต์นี้:
#   แอปรันเป็น container เดียว (ดู Dockerfile) จึงมี process ที่นับอยู่แค่ชุดเดียว
#   ตัวนับจึงตรงกับความจริงทั้งระบบ และไม่ต้องเพิ่ม dependency ภายนอกเลย
# ของจริงที่สเกลเป็นหลาย replica ต้องย้ายตัวนับออกไปอยู่ที่ Redis (INCR + EXPIRE ต่อคีย์)
#   ไม่งั้นคนร้ายยิงกระจายไปทุก replica แล้วแต่ละตัวนับแยกกัน = เพดานจริงคูณจำนวน replica
# ข้อจำกัดอีกข้อ: รีสตาร์ตแอปแล้วตัวนับหายหมด ยอมรับได้เพราะใช้กันยิงถี่ ไม่ใช่กันโกงเงิน
import time

from fastapi import HTTPException, Request

# {คีย์ถัง: [เวลาที่ถูกนับ (epoch seconds), ...]} — sliding window แบบง่าย
_hits: dict[tuple, list[float]] = {}

# เพดานของแต่ละ endpoint รวมไว้ที่เดียว เพื่ออ่าน/ปรับ/monkeypatch ในเทสต์ได้จากจุดเดียว
LOGIN_FAILURES = 10
LOGIN_WINDOW = 5 * 60          # ล็อกอินผิด 10 ครั้งใน 5 นาที
REGISTER_LIMIT = 5
REGISTER_WINDOW = 60 * 60      # สมัคร 5 บัญชีต่อชั่วโมงต่อ IP
TICKET_LIMIT = 30
TICKET_WINDOW = 60             # ขอตั๋วสตรีม 30 ใบต่อนาที


def client_ip(request: Request) -> str:
    """IP ของผู้เรียก — อยู่หลัง reverse proxy ให้เชื่อ X-Forwarded-For ตัวซ้ายสุด

    ของจริงต้องตั้ง proxy ให้เขียน header นี้เองเท่านั้น (ลูกค้าปลอมมาได้ถ้าเปิดรับตรง ๆ)
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _recent(bucket: tuple, window: int) -> list[float]:
    """รายการเวลาที่ยังอยู่ในกรอบเวลา — เก็บกวาดของเก่าไปด้วย dict จึงไม่โตไม่หยุด"""
    cutoff = time.monotonic() - window
    kept = [t for t in _hits.get(bucket, []) if t > cutoff]
    if kept:
        _hits[bucket] = kept
    else:
        _hits.pop(bucket, None)
    return kept


def _too_many(window: int) -> HTTPException:
    minutes = max(1, round(window / 60))
    return HTTPException(
        status_code=429,
        detail=f"คุณเรียกใช้งานถี่เกินไป กรุณารออีกประมาณ {minutes} นาทีแล้วลองใหม่อีกครั้ง",
        # มาตรฐาน HTTP: บอกให้ client รู้ว่าให้รอกี่วินาทีจึงลองใหม่ได้
        headers={"Retry-After": str(window)},
    )


def guard(bucket: tuple, limit: int, window: int) -> None:
    """ตรวจก่อนทำงาน: ถังเต็มแล้วโยน 429 ทันที (ไม่นับเพิ่ม)"""
    if len(_recent(bucket, window)) >= limit:
        raise _too_many(window)


def record(bucket: tuple, window: int) -> None:
    """นับ 1 ครั้งลงถัง — เรียกเฉพาะเหตุการณ์ที่ต้องการจำกัด (เช่น ล็อกอิน "ผิด")"""
    _recent(bucket, window)
    _hits.setdefault(bucket, []).append(time.monotonic())


def hit(bucket: tuple, limit: int, window: int) -> None:
    """ตรวจแล้วนับในก้าวเดียว — ใช้กับ endpoint ที่จำกัดทุกครั้งที่เรียก"""
    guard(bucket, limit, window)
    record(bucket, window)


def forget(bucket: tuple) -> None:
    """ล้างตัวนับของถังนี้ (ล็อกอินสำเร็จแล้วต้องไม่เหลือโทษจากครั้งที่พิมพ์ผิด)"""
    _hits.pop(bucket, None)


def reset() -> None:
    """ล้างตัวนับทั้งหมด — ใช้ในเทสต์เพื่อให้แต่ละเทสต์เริ่มจากศูนย์"""
    _hits.clear()

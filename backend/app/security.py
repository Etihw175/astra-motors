# ระบบยืนยันตัวตน: แฮชรหัสผ่าน + จัดการ session token (Bearer)
# หมายเหตุการสอน: ใช้ PBKDF2-HMAC-SHA256 จาก standard library ของ Python
# จึงไม่ต้องติดตั้ง package เพิ่ม และ "ห้ามเก็บรหัสผ่านเป็น plain text" เด็ดขาด
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .data import SEED_USERS, USER_SEQ, USERS

PBKDF2_ITERATIONS = 120_000
TOKEN_TTL_HOURS = 8            # token หมดอายุใน 8 ชั่วโมง
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.]{4,20}$")

# session store แบบ in-memory: token -> {"user_id": int, "expires_at": datetime}
# (สัปดาห์ถัดไปย้ายไปเก็บใน PostgreSQL หรือเปลี่ยนเป็น JWT ได้ทันที เพราะแยกไฟล์ไว้แล้ว)
SESSIONS: dict[str, dict] = {}

# auto_error=False เพื่อให้เราตอบข้อความภาษาไทยเองแทน error มาตรฐานของ FastAPI
bearer_scheme = HTTPBearer(auto_error=False, description="ใส่ token ที่ได้จาก POST /api/login")


# ---------- รหัสผ่าน ----------

def hash_password(password: str) -> str:
    """คืนค่ารูปแบบ pbkdf2_sha256$<iterations>$<salt>$<hash> เก็บลงฐานข้อมูลได้เลย"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    """ตรวจรหัสผ่านโดยใช้ compare_digest กัน timing attack"""
    try:
        algorithm, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    computed = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations)
    ).hex()
    return hmac.compare_digest(computed, digest)


def password_problem(password: str) -> str | None:
    """คืนข้อความอธิบายถ้ารหัสผ่านไม่ผ่านเกณฑ์ ไม่งั้นคืน None"""
    if len(password) < 8:
        return "รหัสผ่านต้องยาวอย่างน้อย 8 ตัวอักษร"
    if not any(c.isalpha() for c in password):
        return "รหัสผ่านต้องมีตัวอักษรอย่างน้อย 1 ตัว"
    if not any(c.isdigit() for c in password):
        return "รหัสผ่านต้องมีตัวเลขอย่างน้อย 1 ตัว"
    return None


# ---------- token / session ----------

def create_session(user_id: int) -> dict:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=TOKEN_TTL_HOURS)
    SESSIONS[token] = {"user_id": user_id, "expires_at": expires_at}
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
    }


def destroy_session(token: str) -> bool:
    return SESSIONS.pop(token, None) is not None


def destroy_sessions_of(user_id: int) -> int:
    """เตะ session ทั้งหมดของผู้ใช้คนนี้ (ใช้ตอนเปลี่ยนรหัสผ่าน/ลบบัญชี)"""
    tokens = [t for t, s in SESSIONS.items() if s["user_id"] == user_id]
    for t in tokens:
        SESSIONS.pop(t, None)
    return len(tokens)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """Dependency: ทุก endpoint ที่ต้องล็อกอินให้ใส่ตัวนี้ แล้วจะได้ dict ของ user กลับมา"""
    if credentials is None or not credentials.credentials:
        raise _unauthorized("กรุณาเข้าสู่ระบบก่อนใช้งาน")

    session = SESSIONS.get(credentials.credentials)
    if session is None:
        raise _unauthorized("token ไม่ถูกต้องหรือถูกยกเลิกแล้ว กรุณาเข้าสู่ระบบใหม่")
    if session["expires_at"] < datetime.now():
        SESSIONS.pop(credentials.credentials, None)
        raise _unauthorized("เซสชันหมดอายุแล้ว กรุณาเข้าสู่ระบบใหม่")

    user = USERS.get(session["user_id"])
    if user is None:
        SESSIONS.pop(credentials.credentials, None)
        raise _unauthorized("ไม่พบบัญชีผู้ใช้นี้แล้ว")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="บัญชีนี้ถูกระงับการใช้งาน")

    # แนบ token ไว้ให้ /logout เอาไปลบ session ได้โดยไม่ต้องอ่าน header ซ้ำ
    return {**user, "_token": credentials.credentials}


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency: เฉพาะผู้ดูแลระบบ (ใช้กับ endpoint ที่ดู/ลบข้อมูลคนอื่น)"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="ต้องเป็นผู้ดูแลระบบเท่านั้น")
    return user


def can_touch(actor: dict, user_id: int) -> bool:
    """เจ้าของบัญชีเอง หรือผู้ดูแลระบบ เท่านั้นที่แก้/ดูข้อมูลคนนั้นได้"""
    return actor["role"] == "admin" or actor["id"] == user_id


def public_user(user: dict) -> dict:
    """ตัด password_hash ออกเสมอก่อนส่งออกทาง API"""
    return {k: v for k, v in user.items() if not k.startswith("_") and k != "password_hash"}


# ---------- สร้างบัญชี ----------

def next_user_id() -> int:
    USER_SEQ["value"] += 1
    return USER_SEQ["value"]


def build_user(username: str, password: str, full_name: str, email: str,
               phone: str, role: str = "customer") -> dict:
    """ประกอบ record ผู้ใช้ 1 คน (แฮชรหัสผ่านให้เรียบร้อย) แล้วเก็บลง USERS"""
    user = {
        "id": next_user_id(),
        "username": username,
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "role": role,
        "is_active": True,
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    USERS[user["id"]] = user
    return user


def find_by_username(username: str) -> dict | None:
    lowered = username.strip().lower()
    return next((u for u in USERS.values() if u["username"].lower() == lowered), None)


def find_by_email(email: str) -> dict | None:
    lowered = email.strip().lower()
    return next((u for u in USERS.values() if u["email"].lower() == lowered), None)


def seed_users() -> None:
    """สร้างบัญชีตัวอย่างตอนแอปเริ่มทำงาน (เรียกครั้งเดียวจาก main.py)"""
    if USERS:
        return
    for seed in SEED_USERS:
        build_user(
            username=seed["username"],
            password=seed["password"],
            full_name=seed["full_name"],
            email=seed["email"],
            phone=seed["phone"],
            role=seed["role"],
        )

# ระบบยืนยันตัวตน: แฮชรหัสผ่าน + จัดการ session token (Bearer) — เก็บในฐานข้อมูล
# หมายเหตุการสอน: ใช้ PBKDF2-HMAC-SHA256 จาก standard library ของ Python
# จึงไม่ต้องติดตั้ง package เพิ่ม และ "ห้ามเก็บรหัสผ่านเป็น plain text" เด็ดขาด
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session, delete, func, select

from .database import get_session
from .models import AuthSession, User, now

PBKDF2_ITERATIONS = 120_000
TOKEN_TTL_HOURS = 8            # token หมดอายุใน 8 ชั่วโมง
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.]{4,20}$")

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

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(db: Session, user_id: int) -> dict:
    token = secrets.token_urlsafe(32)
    expires_at = now() + timedelta(hours=TOKEN_TTL_HOURS)
    db.add(AuthSession(token_hash=_token_hash(token), user_id=user_id, expires_at=expires_at))
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
    }


def destroy_session(db: Session, token: str) -> bool:
    session = db.get(AuthSession, _token_hash(token))
    if session is None:
        return False
    db.delete(session)
    db.commit()
    return True


def destroy_sessions_of(db: Session, user_id: int) -> None:
    """เตะ session ทั้งหมดของผู้ใช้คนนี้ (ใช้ตอนเปลี่ยนรหัสผ่าน/ระงับ/ลบบัญชี) — ผู้เรียกเป็นคน commit"""
    db.exec(delete(AuthSession).where(AuthSession.user_id == user_id))


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _resolve_user(db: Session, token: str) -> User:
    session = db.get(AuthSession, _token_hash(token))
    if session is None:
        raise _unauthorized("token ไม่ถูกต้องหรือถูกยกเลิกแล้ว กรุณาเข้าสู่ระบบใหม่")
    if session.expires_at < datetime.now():
        db.delete(session)
        db.commit()
        raise _unauthorized("เซสชันหมดอายุแล้ว กรุณาเข้าสู่ระบบใหม่")

    user = db.get(User, session.user_id)
    if user is None:
        raise _unauthorized("ไม่พบบัญชีผู้ใช้นี้แล้ว")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="บัญชีนี้ถูกระงับการใช้งาน")
    return user


def current_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Dependency: คืน token ดิบจาก header (ใช้ตอน logout เพื่อลบ session นั้น)"""
    if credentials is None or not credentials.credentials:
        raise _unauthorized("กรุณาเข้าสู่ระบบก่อนใช้งาน")
    return credentials.credentials


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_session),
) -> User:
    """Dependency: ทุก endpoint ที่ต้องล็อกอินให้ใส่ตัวนี้ แล้วจะได้ User กลับมา"""
    if credentials is None or not credentials.credentials:
        raise _unauthorized("กรุณาเข้าสู่ระบบก่อนใช้งาน")
    return _resolve_user(db, credentials.credentials)


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_session),
) -> Optional[User]:
    """Dependency: endpoint ที่ใช้ได้ทั้ง guest และสมาชิก (เช่น จองทดลองขับ)

    ถ้าล็อกอินอยู่จะผูกข้อมูลเข้าบัญชี — token เสีย/หมดอายุให้ถือเป็น guest แทนการ error
    """
    if credentials is None or not credentials.credentials:
        return None
    try:
        return _resolve_user(db, credentials.credentials)
    except HTTPException:
        return None


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency: เฉพาะผู้ดูแลระบบ (ใช้กับ endpoint ที่ดู/ลบข้อมูลคนอื่น)"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="ต้องเป็นผู้ดูแลระบบเท่านั้น")
    return user


def can_touch(actor: User, owner_id: int | None) -> bool:
    """เจ้าของข้อมูลเอง หรือผู้ดูแลระบบ เท่านั้นที่ดู/แก้ข้อมูลนั้นได้"""
    return actor.role == "admin" or actor.id == owner_id


def public_user(user: User) -> dict:
    """ส่งออกเฉพาะฟิลด์ที่เปิดเผยได้ — ไม่มี password_hash เด็ดขาด"""
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


# ---------- สร้าง/ค้นหาบัญชี ----------

def build_user(db: Session, username: str, password: str, full_name: str, email: str,
               phone: str, role: str = "customer") -> User:
    """สร้างผู้ใช้ 1 คน (แฮชรหัสผ่านให้เรียบร้อย) แล้วบันทึกลงฐานข้อมูล"""
    user = User(
        username=username,
        full_name=full_name,
        email=email,
        phone=phone,
        role=role,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def find_by_username(db: Session, username: str) -> User | None:
    lowered = username.strip().lower()
    return db.exec(select(User).where(func.lower(User.username) == lowered)).first()


def find_by_email(db: Session, email: str) -> User | None:
    lowered = email.strip().lower()
    return db.exec(select(User).where(func.lower(User.email) == lowered)).first()

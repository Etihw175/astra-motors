# Router: จัดการข้อมูลผู้ใช้ (User Management)
# กติกาสิทธิ์: เจ้าของบัญชีดู/แก้ของตัวเองได้, ผู้ดูแลระบบ (admin) ดู/แก้/ลบได้ทุกคน
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from ..data import USERS
from ..schemas import UserOut, UserPage, UserUpdate
from ..security import (
    USERNAME_RE,
    can_touch,
    destroy_sessions_of,
    find_by_email,
    find_by_username,
    get_current_user,
    public_user,
    require_admin,
)

router = APIRouter(prefix="/api", tags=["users"])


def _get_or_404(user_id: int) -> dict:
    user = USERS.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="ไม่พบผู้ใช้รายนี้")
    return user


@router.get("/users", response_model=UserPage, summary="ดึงข้อมูล user ทั้งหมด (pagination)")
def list_users(
    page: int = Query(1, ge=1, description="หน้าที่ต้องการ เริ่มที่ 1"),
    per_page: int = Query(10, ge=1, le=100, description="จำนวนต่อหน้า สูงสุด 100"),
    q: str | None = Query(None, description="ค้นหาจาก username / ชื่อ / อีเมล"),
    role: str | None = Query(None, description="กรองตามสิทธิ์: customer หรือ admin"),
    _admin=Depends(require_admin),
):
    """รายชื่อผู้ใช้ทั้งหมดแบบแบ่งหน้า — เฉพาะผู้ดูแลระบบ

    ป้องกันการดึงข้อมูลทั้งตารางในครั้งเดียว (ทั้งช้าและเสี่ยงข้อมูลรั่ว)
    """
    rows = sorted(USERS.values(), key=lambda u: u["id"])

    if q:
        needle = q.strip().lower()
        rows = [
            u for u in rows
            if needle in u["username"].lower()
            or needle in u["full_name"].lower()
            or needle in u["email"].lower()
        ]
    if role:
        if role not in ("customer", "admin"):
            raise HTTPException(status_code=400, detail="role ต้องเป็น customer หรือ admin")
        rows = [u for u in rows if u["role"] == role]

    total = len(rows)
    total_pages = max(1, -(-total // per_page))   # ปัดขึ้น
    start = (page - 1) * per_page
    items = [public_user(u) for u in rows[start:start + per_page]]

    return {
        "items": items,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/users/{user_id}", response_model=UserOut, summary="ดึงข้อมูล user รายคน")
def get_user(user_id: int = Path(..., ge=1), current=Depends(get_current_user)):
    """ดูข้อมูลผู้ใช้รายคน — ดูของตัวเองได้เสมอ, ดูของคนอื่นได้เฉพาะผู้ดูแลระบบ"""
    if not can_touch(current, user_id):
        raise HTTPException(status_code=403, detail="ดูข้อมูลของผู้ใช้รายอื่นไม่ได้")
    return public_user(_get_or_404(user_id))


@router.put("/users/{user_id}", response_model=UserOut, summary="แก้ไขข้อมูล user")
def update_user(
    body: UserUpdate,
    user_id: int = Path(..., ge=1),
    current=Depends(get_current_user),
):
    """แก้ข้อมูลผู้ใช้ — ส่งมาเฉพาะฟิลด์ที่ต้องการแก้

    ฟิลด์ `role` และ `is_active` เป็นสิทธิ์ของผู้ดูแลระบบเท่านั้น
    (ถ้าไม่กันไว้ ผู้ใช้ทั่วไปจะยกระดับตัวเองเป็น admin ได้)
    """
    if not can_touch(current, user_id):
        raise HTTPException(status_code=403, detail="แก้ไขข้อมูลของผู้ใช้รายอื่นไม่ได้")
    user = _get_or_404(user_id)

    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="ไม่มีข้อมูลที่ต้องการแก้ไข")

    is_admin = current["role"] == "admin"
    if ("role" in changes or "is_active" in changes) and not is_admin:
        raise HTTPException(status_code=403, detail="เฉพาะผู้ดูแลระบบเท่านั้นที่แก้สิทธิ์/สถานะบัญชีได้")
    if "role" in changes and changes["role"] not in ("customer", "admin"):
        raise HTTPException(status_code=400, detail="role ต้องเป็น customer หรือ admin")

    if "email" in changes:
        owner = find_by_email(changes["email"])
        if owner and owner["id"] != user_id:
            raise HTTPException(status_code=409, detail="อีเมลนี้ถูกใช้โดยบัญชีอื่นแล้ว")

    # admin ห้ามถอดสิทธิ์/ระงับบัญชีตัวเอง จนไม่เหลือ admin ในระบบ
    if user["role"] == "admin" and (changes.get("role") == "customer" or changes.get("is_active") is False):
        admins_left = [u for u in USERS.values() if u["role"] == "admin" and u["is_active"] and u["id"] != user_id]
        if not admins_left:
            raise HTTPException(status_code=400, detail="ต้องมีผู้ดูแลระบบที่ใช้งานได้อย่างน้อย 1 บัญชี")

    for key, value in changes.items():
        user[key] = value.strip() if isinstance(value, str) else value
    user["updated_at"] = datetime.now().isoformat(timespec="seconds")

    # ถูกระงับบัญชีเมื่อไร ให้ token ที่ค้างอยู่ใช้ไม่ได้ทันที
    if changes.get("is_active") is False:
        destroy_sessions_of(user_id)

    return public_user(user)


@router.delete("/users/{user_id}", status_code=204, summary="ลบ user")
def delete_user(user_id: int = Path(..., ge=1), admin=Depends(require_admin)):
    """ลบผู้ใช้ — เฉพาะผู้ดูแลระบบ และห้ามลบบัญชีตัวเอง (กันเผลอลบ admin คนสุดท้าย)"""
    _get_or_404(user_id)
    if admin["id"] == user_id:
        raise HTTPException(status_code=400, detail="ลบบัญชีของตัวเองไม่ได้")

    destroy_sessions_of(user_id)
    USERS.pop(user_id, None)
    # status 204 = สำเร็จแต่ไม่มีเนื้อหาตอบกลับ


@router.get("/check-username/{name}", summary="ตรวจสอบว่า username ว่างไหม")
def check_username(name: str = Path(..., min_length=1, max_length=40)):
    """ให้หน้าสมัครสมาชิกเรียกเช็คแบบ real-time ก่อนกดปุ่มสมัคร (ไม่ต้องล็อกอิน)"""
    valid = bool(USERNAME_RE.match(name))
    taken = find_by_username(name) is not None
    return {
        "username": name,
        "valid": valid,
        "available": valid and not taken,
        "reason": (
            None if valid and not taken
            else "username ใช้ได้เฉพาะ a-z, 0-9, _ และ . ความยาว 4-20 ตัวอักษร" if not valid
            else "username นี้ถูกใช้แล้ว"
        ),
    }

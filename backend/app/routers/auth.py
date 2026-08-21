# Router: ระบบสมาชิก (สมัคร / เข้าสู่ระบบ / ออกจากระบบ / เปลี่ยนรหัสผ่าน)
# ทุก endpoint ที่ต้องล็อกอินใช้ Dependency get_current_user ตรวจ Bearer token ให้
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import LoginCreate, PasswordChange, RegisterCreate, TokenOut, UserOut
from ..security import (
    USERNAME_RE,
    build_user,
    create_session,
    destroy_session,
    destroy_sessions_of,
    find_by_email,
    find_by_username,
    get_current_user,
    hash_password,
    password_problem,
    public_user,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201,
             summary="สมัครสมาชิก")
def register(body: RegisterCreate):
    """สมัครสมาชิกใหม่ แล้วเข้าสู่ระบบให้อัตโนมัติ (คืน token มาพร้อมกันเลย)"""
    if not USERNAME_RE.match(body.username):
        raise HTTPException(
            status_code=400,
            detail="username ใช้ได้เฉพาะ a-z, 0-9, _ และ . ความยาว 4-20 ตัวอักษร",
        )
    if find_by_username(body.username):
        raise HTTPException(status_code=409, detail="username นี้ถูกใช้แล้ว กรุณาเลือกชื่ออื่น")
    if find_by_email(body.email):
        raise HTTPException(status_code=409, detail="อีเมลนี้ถูกใช้สมัครไปแล้ว")

    problem = password_problem(body.password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)

    user = build_user(
        username=body.username.strip(),
        password=body.password,
        full_name=body.full_name.strip(),
        email=body.email.strip(),
        phone=body.phone.strip(),
        role="customer",   # สมัครเองได้สิทธิ์ลูกค้าเสมอ ป้องกันคนยกระดับตัวเองเป็น admin
    )
    return {**create_session(user["id"]), "user": public_user(user)}


@router.post("/login", response_model=TokenOut, summary="เข้าสู่ระบบ")
def login(body: LoginCreate):
    """เข้าสู่ระบบด้วย username หรืออีเมล — สำเร็จแล้วได้ Bearer token ไปใช้กับ endpoint อื่น"""
    user = find_by_username(body.username) or find_by_email(body.username)

    # ข้อความ error เดียวกันทั้งกรณี "ไม่มี user" และ "รหัสผิด"
    # เพื่อไม่ให้คนเดาได้ว่ามี username นี้อยู่จริงหรือไม่ (user enumeration)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="username หรือรหัสผ่านไม่ถูกต้อง")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="บัญชีนี้ถูกระงับการใช้งาน กรุณาติดต่อเจ้าหน้าที่")

    return {**create_session(user["id"]), "user": public_user(user)}


@router.post("/logout", summary="ออกจากระบบ")
def logout(current=Depends(get_current_user)):
    """ยกเลิก token ปัจจุบัน — เรียกซ้ำด้วย token เดิมจะได้ 401 เพราะ token ถูกลบไปแล้ว"""
    destroy_session(current["_token"])
    return {"message": "ออกจากระบบเรียบร้อย"}


@router.post("/change-password", summary="เปลี่ยนรหัสผ่าน")
def change_password(body: PasswordChange, current=Depends(get_current_user)):
    """เปลี่ยนรหัสผ่านของตัวเอง ต้องยืนยันรหัสผ่านเดิมเสมอ"""
    user = current
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="รหัสผ่านเดิมไม่ถูกต้อง")
    if body.new_password == body.current_password:
        raise HTTPException(status_code=400, detail="รหัสผ่านใหม่ต้องไม่ซ้ำกับรหัสผ่านเดิม")

    problem = password_problem(body.new_password)
    if problem:
        raise HTTPException(status_code=400, detail=problem)

    from ..data import USERS   # import ตรงนี้เพื่อเลี่ยง import วนกันตอนโหลดโมดูล
    record = USERS[user["id"]]
    record["password_hash"] = hash_password(body.new_password)
    record["updated_at"] = datetime.now().isoformat(timespec="seconds")

    # เปลี่ยนรหัสผ่านแล้วต้องเตะทุกอุปกรณ์ออก เพื่อความปลอดภัย
    destroy_sessions_of(user["id"])
    return {"message": "เปลี่ยนรหัสผ่านเรียบร้อย กรุณาเข้าสู่ระบบใหม่อีกครั้ง"}


@router.get("/me", response_model=UserOut, tags=["users"], summary="ดึงข้อมูลตัวเอง")
def me(current=Depends(get_current_user)):
    """คืนข้อมูลของเจ้าของ token ที่แนบมา"""
    return public_user(current)

# Router: อัปโหลดเอกสารประกอบสินเชื่อ (journey ขั้นตอน 5: "อัปโหลดเอกสารผ่านระบบ" ไม่ต้องถือไปโชว์รูม)
# รับเฉพาะ PDF/JPG/PNG ไม่เกิน 5 MB — ตรวจทั้งนามสกุลและ "ลายเซ็น" ของไฟล์ (magic bytes)
# กันคนเปลี่ยนชื่อไฟล์อันตรายเป็น .pdf แล้วอัปโหลด
import os
import secrets

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlmodel import Session, select

from ..database import get_session
from ..models import Document, User
from ..security import can_touch, get_current_user

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_BYTES = 5 * 1024 * 1024
KINDS = {"id_card", "income", "other"}
SIGNATURES = {
    "application/pdf": (b"%PDF",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


MAX_FILENAME = 120


def safe_filename(raw: str | None) -> str:
    """ชื่อไฟล์ที่เก็บลงฐานข้อมูลได้อย่างปลอดภัย

    ชื่อไฟล์มาจากผู้ใช้ จึงถือเป็นข้อมูลไม่น่าเชื่อถือ:
      - basename ตัด path ทิ้ง ("../../evil.pdf" -> "evil.pdf") กัน path traversal
        ถ้าวันหน้ามีการเขียนไฟล์ลงดิสก์ หรือเอาชื่อไปใส่ header Content-Disposition
      - ตัดอักขระควบคุม (รวม \\r\\n) กันคนแทรกบรรทัดใหม่เข้า header / ปลอม log
      - ยาวไม่เกิน 120 ตัวอักษร ให้พอดีคอลัมน์และไม่ทำให้หน้าเว็บเพี้ยน
    """
    name = (raw or "").replace("\\", "/")        # Windows ส่งมาด้วย \\ ซึ่ง basename ของ POSIX ไม่รู้จัก
    name = os.path.basename(name).strip()
    name = "".join(ch for ch in name if ch.isprintable())
    return name[:MAX_FILENAME] or "document"


def _detect_type(head: bytes) -> str | None:
    for content_type, magic in SIGNATURES.items():
        if any(head.startswith(m) for m in magic):
            return content_type
    return None


def _document_out(doc: Document) -> dict:
    return {
        "id": doc.id,
        "kind": doc.kind,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "size": doc.size,
        "created_at": doc.created_at.isoformat(),
    }


@router.post("", status_code=201, summary="อัปโหลดเอกสาร (PDF/JPG/PNG ≤ 5 MB)")
async def upload_document(
    file: UploadFile = File(...),
    kind: str = Form("other", description="id_card | income | other"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    if kind not in KINDS:
        raise HTTPException(status_code=400, detail="ประเภทเอกสารไม่ถูกต้อง")
    data = await file.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="ไฟล์ว่างเปล่า")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="ไฟล์ใหญ่เกิน 5 MB")
    content_type = _detect_type(data[:8])
    if content_type is None:
        raise HTTPException(status_code=415, detail="รองรับเฉพาะไฟล์ PDF, JPG และ PNG")

    doc = Document(
        id=secrets.token_hex(8),
        user_id=user.id,
        kind=kind,
        filename=safe_filename(file.filename),
        content_type=content_type,
        size=len(data),
        data=data,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _document_out(doc)


@router.get("", summary="เอกสารที่ฉันอัปโหลด")
def my_documents(user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    rows = db.exec(select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())).all()
    return [_document_out(d) for d in rows]


@router.get("/{doc_id}", summary="ดาวน์โหลดเอกสาร (เจ้าของหรือผู้ดูแล)")
def download_document(doc_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    doc = db.get(Document, doc_id)
    if doc is None or not can_touch(user, doc.user_id):
        raise HTTPException(status_code=404, detail="ไม่พบเอกสาร")
    return Response(
        content=doc.data,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.id}"'},
    )

"""เทสต์ Payment service — จ่ายเงินจองก่อน แล้วจึงออกใบจอง (journey ขั้นตอน 5)

สิ่งที่ต้องกันไว้ให้ไม่พังในอนาคต:
- QR ที่สร้างเป็น EMVCo จริง (ขึ้นต้น 000201 + CRC16 ท้ายสตริงถูกต้อง) ไม่ใช่สตริงปลอม
- ใบจองออก "หลัง" ยืนยันเงินเท่านั้น และตอนออกต้องได้แจ้งเตือน + คะแนนเหมือนเส้นทางเดิม
- ยืนยันซ้ำ / รายการของคนอื่น / หมดอายุ — ต้องไม่ออกใบจองเกินมาใบที่สอง
"""
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import engine
from app.main import app
from app.models import Payment
from app.promptpay import crc16_ccitt

client = TestClient(app)

BOOKING_FEE = 200_000


def register(username: str) -> dict:
    res = client.post("/api/register", json={
        "username": username,
        "password": "paytest123",
        "full_name": "ทดสอบ ชำระเงิน",
        "email": f"{username}@example.com",
        "phone": "0812223333",
    })
    assert res.status_code == 201, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def start_payment(headers: dict, method: str = "promptpay", **extra) -> dict:
    body = {
        "car_id": "porsche-911", "color_id": "guards-red", "option_ids": [],
        "name": "ทดสอบ ชำระเงิน", "phone": "0812223333", "email": "pay@example.com",
        "method": method,
    }
    body.update(extra)
    res = client.post("/api/payments", headers=headers, json=body)
    assert res.status_code == 201, res.text
    return res.json()


def _expire_now(payment_id: str) -> None:
    """ดันวันหมดอายุให้เป็นอดีต — เลียนแบบสถานการณ์ลูกค้าเปิดหน้า QR ทิ้งไว้เกิน 15 นาที"""
    with Session(engine) as db:
        record = db.get(Payment, payment_id)
        record.expires_at = datetime.now() - timedelta(minutes=1)
        db.add(record)
        db.commit()


# ---------- สร้างรายการชำระเงิน ----------

def test_payment_requires_login():
    assert client.post("/api/payments", json={}).status_code in (401, 422)
    assert client.get("/api/payments/PAY-0000-ABCDEF").status_code == 401


def test_promptpay_payment_returns_real_emvco_payload_and_qr():
    headers = register("payer01")
    payment = start_payment(headers)

    assert payment["id"].startswith("PAY-")
    assert payment["status"] == "pending" and payment["amount"] == BOOKING_FEE
    assert payment["simulation"] is True          # ต้องกำกับทุก response ว่าเป็นบัญชีสมมติ
    assert payment["reservation_code"] is None    # ยังไม่จ่าย ยังไม่มีใบจอง
    assert 0 < payment["expires_in"] <= 15 * 60

    payload = payment["qr_payload"]
    assert payload.startswith("000201")                   # tag 00 = 01, tag 01 = 12 (ระบุยอด)
    assert "5303764" in payload                           # tag 53 สกุลเงินบาท
    assert f"5409{BOOKING_FEE}.00" in payload             # tag 54 ยอดเงินทศนิยม 2 ตำแหน่ง
    assert "5802TH" in payload                            # tag 58 ประเทศ
    assert "0016A000000677010111" in payload              # AID ของพร้อมเพย์ใต้ tag 29
    # คำนวณ CRC ซ้ำจากสตริงที่ตัด 4 ตัวท้ายออก ต้องได้ค่าเดิม
    assert payload[-8:-4] == "6304"
    assert crc16_ccitt(payload[:-4]) == payload[-4:]

    assert payment["qr_svg"].startswith("<svg") and "</svg>" in payment["qr_svg"]


def test_card_payment_never_takes_a_card_number():
    headers = register("payer02")
    payment = start_payment(headers, method="card", card_last4="4242")
    assert payment["method"] == "card" and payment["card_last4"] == "4242"
    assert "qr_payload" not in payment and "qr_svg" not in payment
    # 4 ตัวท้ายต้องเป็นตัวเลข และยาว 4 ตัวเท่านั้น (ฟิลด์นี้ไว้แสดงผล ไม่ใช่ข้อมูลบัตรจริง)
    assert client.post("/api/payments", headers=headers, json={
        "car_id": "porsche-911", "color_id": "guards-red", "option_ids": [],
        "name": "ทดสอบ ชำระเงิน", "phone": "0812223333", "email": "pay@example.com",
        "method": "card", "card_last4": "42xy",
    }).status_code == 400
    assert client.post("/api/payments", headers=headers, json={
        "car_id": "porsche-911", "color_id": "guards-red", "option_ids": [],
        "name": "ทดสอบ ชำระเงิน", "phone": "0812223333", "email": "pay@example.com",
        "method": "card", "card_last4": "123456",   # ยาวเกิน 4 ตัว = ส่งเลขบัตรมาเกินที่จำเป็น
    }).status_code == 422


def test_bad_method_and_unknown_spec_are_rejected():
    headers = register("payer03")
    assert client.post("/api/payments", headers=headers, json={
        "car_id": "porsche-911", "color_id": "guards-red", "option_ids": [],
        "name": "ทดสอบ ชำระเงิน", "phone": "0812223333", "email": "pay@example.com",
        "method": "bitcoin",
    }).status_code == 400
    assert client.post("/api/payments", headers=headers, json={
        "car_id": "porsche-911", "color_id": "ไม่มีสีนี้", "option_ids": [],
        "name": "ทดสอบ ชำระเงิน", "phone": "0812223333", "email": "pay@example.com",
        "method": "promptpay",
    }).status_code == 404


# ---------- ยืนยันการชำระเงิน ----------

def test_confirm_issues_reservation_with_notification_and_points():
    headers = register("payer04")
    before = client.get("/api/loyalty", headers=headers).json()["balance"]
    payment = start_payment(headers)

    # ยังไม่ confirm: ไม่มีใบจอง ไม่มีคะแนน (ของจริงเงินยังไม่เข้าก็ยังไม่ออกใบจอง)
    assert client.get("/api/me/bookings", headers=headers).json()["reservations"] == []
    assert client.get("/api/loyalty", headers=headers).json()["balance"] == before

    paid = client.post(f"/api/payments/{payment['id']}/confirm", headers=headers)
    assert paid.status_code == 200, paid.text
    paid = paid.json()
    assert paid["status"] == "paid" and paid["paid_at"]
    code = paid["reservation_code"]
    assert code and code.startswith("ADR-")

    # ใบจองที่ออกมาต้องใช้งานได้จริงเหมือนเส้นทางเดิม
    reservation = client.get(f"/api/reservations/{code}", headers=headers)
    assert reservation.status_code == 200
    reservation = reservation.json()
    assert reservation["booking_fee"] == BOOKING_FEE
    assert reservation["payment_method"] == "promptpay"
    assert reservation["total_price"] == paid["total_price"]
    assert reservation["customer"]["email"] == "pay@example.com"

    # event เดิมยังทำงาน (แจ้งเตือน + คะแนน) และมี event ใหม่ payment.paid เพิ่มมา
    kinds = [n["kind"] for n in client.get("/api/notifications", headers=headers).json()["items"]]
    assert "reservation.created" in kinds and "payment.paid" in kinds
    assert client.get("/api/loyalty", headers=headers).json()["balance"] == before + 2000


def test_double_confirm_is_conflict_and_issues_only_one_reservation():
    headers = register("payer05")
    payment = start_payment(headers)
    first = client.post(f"/api/payments/{payment['id']}/confirm", headers=headers).json()

    again = client.post(f"/api/payments/{payment['id']}/confirm", headers=headers)
    assert again.status_code == 409
    assert client.get(f"/api/payments/{payment['id']}", headers=headers).json()["reservation_code"] \
        == first["reservation_code"]
    assert len(client.get("/api/me/bookings", headers=headers).json()["reservations"]) == 1


def test_other_users_payment_is_not_found():
    headers = register("payer06")
    stranger = register("payer07")
    payment = start_payment(headers)
    assert client.get(f"/api/payments/{payment['id']}", headers=stranger).status_code == 404
    assert client.post(f"/api/payments/{payment['id']}/confirm", headers=stranger).status_code == 404
    assert client.post(f"/api/payments/{payment['id']}/cancel", headers=stranger).status_code == 404


def test_expired_payment_cannot_be_confirmed():
    headers = register("payer08")
    payment = start_payment(headers)
    _expire_now(payment["id"])

    # แค่เปิดดูก็เปลี่ยนสถานะเป็น expired แล้ว (ไม่ต้องรอ cron มากวาด)
    seen = client.get(f"/api/payments/{payment['id']}", headers=headers).json()
    assert seen["status"] == "expired" and seen["expires_in"] == 0

    failed = client.post(f"/api/payments/{payment['id']}/confirm", headers=headers)
    assert failed.status_code == 400
    assert "ใหม่" in failed.json()["detail"]
    assert client.get("/api/me/bookings", headers=headers).json()["reservations"] == []


def test_cancel_marks_payment_failed():
    headers = register("payer09")
    payment = start_payment(headers)
    cancelled = client.post(f"/api/payments/{payment['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "failed"
    # ยกเลิกแล้วยืนยันไม่ได้ และยกเลิกซ้ำไม่ได้
    assert client.post(f"/api/payments/{payment['id']}/confirm", headers=headers).status_code == 400
    assert client.post(f"/api/payments/{payment['id']}/cancel", headers=headers).status_code == 400


def test_cancel_after_paid_points_to_reservation_refund():
    headers = register("payer10")
    payment = start_payment(headers)
    client.post(f"/api/payments/{payment['id']}/confirm", headers=headers)
    blocked = client.post(f"/api/payments/{payment['id']}/cancel", headers=headers)
    assert blocked.status_code == 400 and "ใบจอง" in blocked.json()["detail"]

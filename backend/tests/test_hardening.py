"""เทสต์ของที่ตรวจพบในรอบ QA: ความปลอดภัย, ตรรกะธุรกิจ และช่องว่างของหลังบ้าน

ทุกเทสต์ในไฟล์นี้ "ต้องแดง" ถ้าย้อนโค้ดกลับไปเป็นก่อนแก้ — เขียนคู่กับของที่แก้ทีละข้อ
รันด้วย:  cd backend && pytest -q
"""
import re
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import models, ratelimit
from app.data import CARS, FINANCE_PLANS
from app.database import engine
from app.main import app
from app.routers import loans, notifications
from app.routers.documents import safe_filename

client = TestClient(app)

TOMORROW = (date.today() + timedelta(days=1)).isoformat()
ADMIN = {"username": "admin", "password": "admin1234"}
CUSTOMER = {"username": "somchai", "password": "somchai123"}
PDF = b"%PDF-1.4\n% hardening\n"


def auth_header(credentials: dict) -> dict:
    res = client.post("/api/login", json=credentials)
    assert res.status_code == 200, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def register(username: str, **overrides) -> dict:
    body = {
        "username": username,
        "password": "harden123",
        "full_name": "ทดสอบ ความแข็งแรง",
        "email": f"{username}@example.com",
        "phone": "0812220000",
    }
    res = client.post("/api/register", json={**body, **overrides})
    assert res.status_code == 201, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def pay_and_reserve(headers: dict, car_id: str = "porsche-911", color_id: str = "guards-red",
                    option_ids: list[str] | None = None) -> dict:
    """เส้นทางจริงของลูกค้า: จ่ายเงินจองก่อน แล้วระบบจึงออกใบจอง"""
    pay = client.post("/api/payments", headers=headers, json={
        "car_id": car_id, "color_id": color_id, "option_ids": option_ids or [],
        "name": "ทดสอบ ความแข็งแรง", "phone": "0812220000", "email": "harden@example.com",
        "method": "promptpay",
    })
    assert pay.status_code == 201, pay.text
    confirmed = client.post(f"/api/payments/{pay.json()['id']}/confirm", headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    code = confirmed.json()["reservation_code"]
    return client.get(f"/api/reservations/{code}", headers=headers).json()


def free_slot(showroom_id: str, taken: set[str] | None = None) -> str:
    slots = client.get(f"/api/showrooms/{showroom_id}/slots", params={"date": TOMORROW}).json()["slots"]
    return next(s["time"] for s in slots if s["available"] and s["time"] not in (taken or set()))


# ======================= 1. rate limit =======================

def test_login_blocks_brute_force_and_success_resets_counter():
    register("rl_login")
    wrong = {"username": "rl_login", "password": "ไม่ใช่รหัสนี้1"}

    for _ in range(ratelimit.LOGIN_FAILURES):
        assert client.post("/api/login", json=wrong).status_code == 401
    blocked = client.post("/api/login", json=wrong)
    assert blocked.status_code == 429
    assert "รอ" in blocked.json()["detail"] and blocked.headers["retry-after"]

    # รหัสถูกก็ยังเข้าไม่ได้ระหว่างถูกจำกัด (ไม่งั้นก็เดารหัสต่อได้เรื่อย ๆ)
    assert client.post("/api/login", json={"username": "rl_login", "password": "harden123"}).status_code == 429

    # พิมพ์ผิด 2 ครั้งแล้วเข้าได้ -> ตัวนับต้องถูกล้าง คนพิมพ์ผิดจึงไม่ถูกลงโทษต่อ
    ratelimit.reset()
    assert client.post("/api/login", json=wrong).status_code == 401
    assert client.post("/api/login", json=wrong).status_code == 401
    assert client.post("/api/login", json={"username": "rl_login", "password": "harden123"}).status_code == 200
    for _ in range(ratelimit.LOGIN_FAILURES):
        assert client.post("/api/login", json=wrong).status_code == 401
    assert client.post("/api/login", json=wrong).status_code == 429


def test_register_is_rate_limited_per_ip():
    for i in range(ratelimit.REGISTER_LIMIT):
        register(f"rl_reg{i}")
    over = client.post("/api/register", json={
        "username": "rl_regx", "password": "harden123", "full_name": "ทดสอบ เกินโควตา",
        "email": "rl_regx@example.com", "phone": "0812220000",
    })
    assert over.status_code == 429 and "รอ" in over.json()["detail"]


def test_stream_ticket_is_rate_limited():
    headers = register("rl_ticket")
    for _ in range(ratelimit.TICKET_LIMIT):
        assert client.post("/api/notifications/stream-ticket", headers=headers).status_code == 200
    assert client.post("/api/notifications/stream-ticket", headers=headers).status_code == 429


# ======================= 2. USERNAME_RE =======================

@pytest.mark.parametrize("username", ["okname1\n", "okname1\r\n", "ok name"])
def test_username_with_trailing_newline_is_rejected(username):
    """re.match กับ $ ยอมให้มี newline ปิดท้าย — "name\\n" จึงเคยสมัครผ่าน"""
    res = client.post("/api/register", json={
        "username": username, "password": "harden123", "full_name": "ทดสอบ ชื่อเพี้ยน",
        "email": "weirdname@example.com", "phone": "0812220000",
    })
    assert res.status_code == 400


def test_check_username_rejects_trailing_newline():
    # ส่ง newline แบบ percent-encoded เพราะใส่อักขระควบคุมตรง ๆ ใน URL ไม่ได้
    assert client.get("/api/check-username/okname1%0A").json()["valid"] is False
    assert client.get("/api/check-username/okname1").json()["valid"] is True


# ======================= 3. ตั๋วสตรีม =======================

def _tickets_of(user_id: int) -> int:
    return sum(1 for owner, _ in notifications._stream_tickets.values() if owner == user_id)


def test_logout_and_password_change_drop_outstanding_tickets():
    headers = register("tk_logout")
    user_id = client.get("/api/me", headers=headers).json()["id"]
    ticket = client.post("/api/notifications/stream-ticket", headers=headers).json()["ticket"]
    assert _tickets_of(user_id) == 1

    assert client.post("/api/logout", headers=headers).status_code == 200
    assert _tickets_of(user_id) == 0
    # ตั๋วที่ขอไว้ก่อนออกจากระบบต้องเปิดสตรีมไม่ได้แล้ว
    assert client.get("/api/notifications/stream",
                      params={"ticket": ticket, "max_events": 1}).status_code == 401

    headers = auth_header({"username": "tk_logout", "password": "harden123"})
    client.post("/api/notifications/stream-ticket", headers=headers)
    assert _tickets_of(user_id) == 1
    assert client.post("/api/change-password", headers=headers, json={
        "current_password": "harden123", "new_password": "harden456",
    }).status_code == 200
    assert _tickets_of(user_id) == 0


def test_outstanding_tickets_are_capped_per_user():
    headers = register("tk_cap")
    user_id = client.get("/api/me", headers=headers).json()["id"]
    first = client.post("/api/notifications/stream-ticket", headers=headers).json()["ticket"]
    for _ in range(notifications.MAX_TICKETS_PER_USER):
        client.post("/api/notifications/stream-ticket", headers=headers)
    assert _tickets_of(user_id) == notifications.MAX_TICKETS_PER_USER
    # ใบที่เก่าที่สุดถูกทิ้งไปแล้ว
    assert client.get("/api/notifications/stream",
                      params={"ticket": first, "max_events": 1}).status_code == 401


# ======================= 4. รีวิวไม่ส่ง user_id =======================

def test_public_reviews_hide_author_id_and_expose_is_mine():
    author = register("rv_author")
    pay_and_reserve(author, "ferrari-488", "rosso-corsa")
    created = client.post("/api/reviews", headers=author, json={
        "car_id": "ferrari-488", "rating": 5, "title": "สุดยอด",
        "comment": "ขับสนุกมากและศูนย์บริการดูแลดีเกินคาด",
    })
    assert created.status_code == 201, created.text
    assert "user_id" not in created.json() and created.json()["is_mine"] is True

    public = client.get("/api/reviews", params={"car_id": "ferrari-488"}).json()
    assert public and all("user_id" not in r for r in public)
    assert all(r["is_mine"] is False for r in public)          # ไม่ล็อกอิน = ไม่มีรีวิวของฉัน

    stranger = register("rv_stranger")
    seen = client.get("/api/reviews", params={"car_id": "ferrari-488"}, headers=stranger).json()
    assert all(r["is_mine"] is False for r in seen)

    mine = client.get("/api/reviews", params={"car_id": "ferrari-488"}, headers=author).json()
    assert any(r["is_mine"] for r in mine)
    assert all("user_id" not in r and r["is_mine"] for r in client.get("/api/reviews/mine", headers=author).json())


# ======================= 5. ชื่อไฟล์ที่อัปโหลด =======================

@pytest.mark.parametrize("raw,expected", [
    ("../../evil.pdf", "evil.pdf"),
    ("..\\..\\windows\\evil.pdf", "evil.pdf"),
    ("/etc/passwd", "passwd"),
    ("ok\r\nSet-Cookie: x=1.pdf", "okSet-Cookie: x=1.pdf"),
    ("", "document"),
    ("x" * 300 + ".pdf", "x" * 120),
])
def test_safe_filename_strips_paths_and_control_characters(raw, expected):
    assert safe_filename(raw) == expected


def test_uploaded_filename_is_stored_as_basename():
    headers = register("doc_path")
    res = client.post("/api/documents", headers=headers, data={"kind": "other"},
                      files={"file": ("../../evil.pdf", PDF, "application/pdf")})
    assert res.status_code == 201, res.text
    assert res.json()["filename"] == "evil.pdf"


# ======================= 6. security headers =======================

@pytest.mark.parametrize("path", ["/api/health", "/api/cars"])
def test_security_headers_are_present(path):
    headers = client.get(path).headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "same-origin"
    # ตั้งใจไม่ใส่ CSP (จะพัง model-viewer/Google Fonts) — ดูเหตุผลใน app/main.py
    assert "content-security-policy" not in headers


# ======================= 7. ใบจองที่ไม่มีการชำระเงิน = เฉพาะพนักงาน =======================

def test_legacy_reservation_endpoint_is_admin_only():
    body = {
        "car_id": "porsche-911", "color_id": "guards-red", "option_ids": [],
        "name": "ทดสอบ ปั๊มคะแนน", "phone": "0812220000", "email": "farm@example.com",
        "payment_method": "promptpay",
    }
    customer = register("rsv_farmer")
    before = client.get("/api/loyalty", headers=customer).json()["balance"]
    assert client.post("/api/reservations", headers=customer, json=body).status_code == 403
    assert client.get("/api/loyalty", headers=customer).json()["balance"] == before   # ไม่ได้คะแนนฟรี
    assert client.post("/api/reservations", json=body).status_code == 401

    # พนักงานยังออกใบจองให้ลูกค้า walk-in ที่จ่ายเงินสดหน้าเคาน์เตอร์ได้
    walk_in = client.post("/api/reservations", headers=auth_header(ADMIN), json=body)
    assert walk_in.status_code == 201, walk_in.text
    assert walk_in.json()["code"].startswith("ADR-")


# ======================= 9-10. โปรโมชั่น =======================

def test_car_payload_carries_computed_promotion_status():
    for car in client.get("/api/cars").json():
        assert "promotion_status" in car
        if car["promotion"]:
            status = car["promotion_status"]
            assert status["expires"] == car["promotion"]["expires"]
            assert status["active"] is (date.fromisoformat(status["expires"]) >= date.today())
        else:
            assert car["promotion_status"] is None

    # GT-R โปรฯ หมดอายุแล้ว (2026-08-15) ต้องยังส่ง promotion มาเหมือนเดิม แต่ติดธงว่าหมดแล้ว
    gtr = client.get("/api/cars/gtr-r35").json()
    assert gtr["promotion"]["title"] and gtr["promotion_status"]["active"] is False
    assert gtr["promotion_status"]["days_left"] == 0

    porsche = client.get("/api/cars/porsche-911").json()
    assert porsche["promotion_status"]["active"] is True


def test_promotion_text_matches_a_real_finance_plan():
    """ของเดิมโปรฯ Porsche สัญญา 2.29% ซึ่งไม่มีอยู่ในแผนสินเชื่อจริงเลย"""
    rates = {f"{plan['flat_rate']}%" for plan in FINANCE_PLANS}
    # เอาเฉพาะตัวเลขที่มีทศนิยม = อัตราดอกเบี้ย ("30%" คือสัดส่วนเงินดาวน์ ไม่ใช่ดอกเบี้ย)
    promised = [
        word.rstrip(",")
        for car in CARS if car.get("promotion")
        for word in car["promotion"]["title"].split()
        if re.fullmatch(r"\d+\.\d+%", word.rstrip(","))
    ]
    assert promised, "ต้องมีโปรฯ ที่พูดถึงดอกเบี้ยอย่างน้อย 1 รายการ"
    assert all(rate in rates for rate in promised), f"โปรฯ อ้างอัตราที่ไม่มีแผนรองรับ: {promised} / {rates}"


# ======================= 11-12. หลังบ้าน: นัดเข้าศูนย์ =======================

def test_admin_service_list_searches_and_shows_customer_contact():
    admin = auth_header(ADMIN)
    phone = "0898887777"
    headers = register("svc_search", phone=phone, full_name="ค้นหา นัดบริการ")
    booked = client.post("/api/service/appointments", headers=headers, json={
        "car_id": "gtr-r35", "showroom_id": "chiangmai", "date": TOMORROW,
        "time": "10:00", "service_type": "periodic", "mileage_km": 9000, "note": "",
    })
    assert booked.status_code == 201, booked.text
    code = booked.json()["code"]

    for needle in (code, "ค้นหา นัดบริการ", phone, "GT-R"):
        found = client.get("/api/admin/service-appointments", headers=admin,
                           params={"q": needle}).json()
        assert code in {i["code"] for i in found["items"]}, needle

    # ค้นไม่เจอต้องเป็น 0 ไม่ใช่คืนทุกแถว (ของเดิม q ถูกเมินทั้งพารามิเตอร์)
    assert client.get("/api/admin/service-appointments", headers=admin,
                      params={"q": "ไม่มีใครชื่อนี้แน่นอน"}).json()["total"] == 0

    row = next(i for i in client.get("/api/admin/service-appointments", headers=admin,
                                     params={"q": code}).json()["items"])
    assert row["customer"] == {"name": "ค้นหา นัดบริการ", "phone": phone}

    # ฝั่งลูกค้าต้องไม่มีฟิลด์ customer ติดไปด้วย (service_dict ยังเหมือนเดิม)
    assert "customer" not in client.get("/api/service/appointments", headers=headers).json()[0]


# ======================= 13. ค้นหาผู้ใช้ด้วยเบอร์โทร =======================

def test_user_search_matches_phone():
    admin = auth_header(ADMIN)
    register("usr_phone", phone="0876543210", full_name="ค้นด้วย เบอร์โทร")
    found = client.get("/api/users", headers=admin, params={"q": "0876543210"}).json()
    assert found["total"] == 1 and found["items"][0]["username"] == "usr_phone"


# ======================= A. ปั๊มคะแนนด้วยการจอง-ยกเลิกทดลองขับ =======================

def test_cancelled_testdrive_gives_points_back():
    headers = register("td_farmer")
    before = client.get("/api/loyalty", headers=headers).json()["balance"]
    taken: set[str] = set()
    for _ in range(3):
        time = free_slot("bangna", taken)
        taken.add(time)
        booked = client.post("/api/testdrives", headers=headers, json={
            "car_id": "gtr-r35", "showroom_id": "bangna", "date": TOMORROW, "time": time,
            "name": "ทดสอบ ปั๊มคะแนน", "phone": "0812220000", "has_license": True,
        })
        assert booked.status_code == 201, booked.text
        assert client.post(f"/api/testdrives/{booked.json()['code']}/cancel",
                           headers=headers).status_code == 200
    # จอง-ยกเลิกวนเท่าไรก็ต้องไม่ได้คะแนนเพิ่ม
    assert client.get("/api/loyalty", headers=headers).json()["balance"] == before


# ======================= B. ยกเลิกใบจอง -> ยกเลิกสินเชื่อ =======================

def test_cancelling_reservation_cancels_its_loan(monkeypatch):
    headers = register("loan_cancel")
    rsv = pay_and_reserve(headers)
    loan = client.post("/api/loans", headers=headers, json={
        "reservation_code": rsv["code"], "plan_id": "krungthai-leasing",
        "down_payment": round(rsv["total_price"] * 0.3), "term_months": 60,
        "name": "ทดสอบ ยกเลิกสินเชื่อ", "phone": "0812220000", "occupation": "เจ้าของกิจการ",
        "monthly_income": 2_000_000, "consent_pdpa": True,
    })
    assert loan.status_code == 201 and loan.json()["status"] == "reviewing"
    loan_id = loan.json()["id"]

    assert client.post(f"/api/reservations/{rsv['code']}/cancel", headers=headers).status_code == 200

    # ครบเวลาพิจารณาแล้วก็ต้องไม่กลายเป็น approved และต้องไม่มีแจ้งเตือนผลสินเชื่อ
    monkeypatch.setattr(loans, "REVIEW_SECONDS", 0)
    after = client.get(f"/api/loans/{loan_id}", headers=headers).json()
    assert after["status"] == "cancelled"
    assert "ยกเลิก" in after["result"]["message"]

    kinds = [n["kind"] for n in client.get("/api/notifications", headers=headers).json()["items"]]
    assert "loan.decided" not in kinds


# ======================= C. ทางเลือกสินเชื่อต้องเป็นไปได้จริง =======================

def test_rejected_loan_alternatives_stay_realistic_at_tiny_income(monkeypatch):
    headers = register("loan_tiny")
    rsv = pay_and_reserve(headers, "gtr-r35", "gun-metallic")
    assert rsv["total_price"] == 10_500_000
    loan = client.post("/api/loans", headers=headers, json={
        "reservation_code": rsv["code"], "plan_id": "astra-finance",
        "down_payment": 2_625_000, "term_months": 60,
        "name": "ทดสอบ รายได้น้อย", "phone": "0812220000", "occupation": "นักศึกษา",
        "monthly_income": 100, "consent_pdpa": True,
    })
    assert loan.status_code == 201, loan.text

    monkeypatch.setattr(loans, "REVIEW_SECONDS", 0)
    result = client.get(f"/api/loans/{loan.json()['id']}", headers=headers).json()["result"]
    assert result["alternatives"]
    joined = " ".join(result["alternatives"])
    assert "-" not in joined.replace("co-borrower", "")   # ห้ามมีค่างวดติดลบ
    # ห้ามเสนอดาวน์ที่รวมแล้วเกินราคารถ (เคยเสนอ "รวมดาวน์ 10,505,000 บาท" ของรถ 10,500,000)
    assert "รวมดาวน์" not in joined
    assert "รายได้ที่แจ้ง" in joined


# ======================= D. option_ids ที่ไม่รู้จัก =======================

@pytest.mark.parametrize("path,extra", [
    ("/api/payments", {"method": "promptpay"}),
    ("/api/reservations", {"payment_method": "promptpay"}),
])
def test_unknown_option_ids_are_rejected(path, extra):
    headers = auth_header(ADMIN)   # /api/reservations เป็นของพนักงาน จึงใช้สิทธิ์ admin ทั้งคู่
    res = client.post(path, headers=headers, json={
        "car_id": "porsche-911", "color_id": "guards-red", "option_ids": ["bogus", "jetpack"],
        "name": "ทดสอบ ออปชันมั่ว", "phone": "0812220000", "email": "opt@example.com", **extra,
    })
    assert res.status_code == 400, res.text
    assert "bogus" in res.json()["detail"] and "jetpack" in res.json()["detail"]


# ======================= E-F. body เสีย + ข้อความ 422 ภาษาไทย =======================

def test_malformed_utf8_body_is_a_client_error_not_a_crash():
    """lone surrogate เคยทำให้ handler มาตรฐานสะท้อน input กลับแล้ว encode ไม่ได้ -> 500"""
    res = client.post("/api/login", content=b'{"username":"\xed\xa0\x80","password":"x"}',
                      headers={"content-type": "application/json"})
    assert res.status_code in (400, 422), res.status_code
    assert res.json()["detail"]
    assert client.post("/api/login", content=b'{"username":"\xff"}',
                       headers={"content-type": "application/json"}).status_code in (400, 422)
    assert client.post("/api/login", content="ไม่ใช่ json".encode("utf-8"),
                       headers={"content-type": "application/json"}).status_code in (400, 422)


def test_validation_errors_are_thai_and_machine_readable():
    res = client.post("/api/register", json={"username": "no_pass_1"})
    assert res.status_code == 422
    body = res.json()
    assert isinstance(body["detail"], str)                 # หน้าเว็บโชว์ detail เป็นข้อความอยู่แล้ว
    assert "รหัสผ่าน" in body["detail"] and "อีเมล" in body["detail"]
    fields = {f["field"]: f for f in body["fields"]}
    assert fields["password"]["label"] == "รหัสผ่าน"
    assert fields["password"]["message"] == "กรุณากรอกข้อมูลนี้"

    short = client.post("/api/register", json={
        "username": "shortpw1", "password": "ab1", "full_name": "ทดสอบ รหัสสั้น",
        "email": "shortpw@example.com", "phone": "0812220000",
    })
    assert short.status_code == 422
    assert "8 ตัวอักษร" in short.json()["detail"]


# ======================= G. validate ให้เข้มขึ้น =======================

@pytest.mark.parametrize("field,value", [
    ("phone", "abcdefghij"),
    ("phone", "123"),
    ("full_name", "     "),
    ("email", "xxxxx"),
])
def test_register_rejects_junk_fields(field, value):
    res = client.post("/api/register", json={
        "username": "junkfield", "password": "harden123", "full_name": "ทดสอบ ข้อมูลมั่ว",
        "email": "junkfield@example.com", "phone": "0812220000", **{field: value},
    })
    assert res.status_code == 422, res.text


def test_blank_review_comment_earns_no_points():
    headers = register("rv_blank")
    before = client.get("/api/loyalty", headers=headers).json()["balance"]
    res = client.post("/api/reviews", headers=headers, json={
        "car_id": "porsche-911", "rating": 5, "title": "  ", "comment": " " * 20,
    })
    assert res.status_code == 422, res.text
    assert client.get("/api/loyalty", headers=headers).json()["balance"] == before


def test_payment_requires_a_real_email():
    headers = register("pay_email")
    res = client.post("/api/payments", headers=headers, json={
        "car_id": "porsche-911", "color_id": "guards-red", "option_ids": [],
        "name": "ทดสอบ อีเมลมั่ว", "phone": "0812220000", "email": "xxxxx",
        "method": "promptpay",
    })
    assert res.status_code == 422, res.text


# ======================= H-J. ของเล็ก =======================

def test_same_user_cannot_take_two_bays_in_one_slot():
    headers = register("svc_double")
    body = {"car_id": "gtr-r35", "showroom_id": "bangna", "date": TOMORROW,
            "time": "11:30", "service_type": "periodic", "mileage_km": 5000, "note": ""}
    assert client.post("/api/service/appointments", headers=headers, json=body).status_code == 201
    again = client.post("/api/service/appointments", headers=headers, json=body)
    assert again.status_code == 409 and "อยู่แล้ว" in again.json()["detail"]
    # คนอื่นยังจองช่องที่สองของช่วงเวลานี้ได้ตามปกติ
    assert client.post("/api/service/appointments", headers=register("svc_other"),
                       json=body).status_code == 201


def test_booking_dates_are_capped():
    headers = register("far_future")
    res = client.post("/api/testdrives", headers=headers, json={
        "car_id": "gtr-r35", "showroom_id": "bangna", "date": "9999-12-31", "time": "10:00",
        "name": "ทดสอบ อนาคตไกล", "phone": "0812220000", "has_license": True,
    })
    assert res.status_code == 400 and "ล่วงหน้า" in res.json()["detail"]
    too_far = (date.today() + timedelta(days=200)).isoformat()
    assert client.get("/api/showrooms/bangna/slots", params={"date": too_far}).status_code == 400


def test_occupation_has_a_length_limit():
    headers = register("occ_long")
    rsv = pay_and_reserve(headers)
    res = client.post("/api/loans", headers=headers, json={
        "reservation_code": rsv["code"], "plan_id": "krungthai-leasing",
        "down_payment": round(rsv["total_price"] * 0.3), "term_months": 60,
        "name": "ทดสอบ อาชีพยาว", "phone": "0812220000", "occupation": "ก" * 5000,
        "monthly_income": 2_000_000, "consent_pdpa": True,
    })
    assert res.status_code == 422, res.text


# ======================= 8. ปิดงานบริการล่วงหน้า =======================

def test_service_job_cannot_be_closed_before_its_date():
    """นัดอีก 20 วันข้างหน้าต้องปิดงานไม่ได้ (complete_testdrive กันไว้อยู่แล้ว แต่ของบริการไม่กัน)"""
    admin = auth_header(ADMIN)
    headers = register("svc_early")
    booked = client.post("/api/service/appointments", headers=headers, json={
        "car_id": "porsche-911", "showroom_id": "rama3", "date": TOMORROW,
        "time": "08:30", "service_type": "periodic", "mileage_km": 7000, "note": "",
    })
    assert booked.status_code == 201, booked.text
    code = booked.json()["code"]

    with Session(engine) as db:                      # เลื่อนไป 20 วันข้างหน้าตรงฐานข้อมูล
        record = db.get(models.ServiceAppointment, code)
        record.date = date.today() + timedelta(days=20)
        db.add(record)
        db.commit()

    early = client.post(f"/api/admin/service-appointments/{code}/complete", headers=admin)
    assert early.status_code == 400
    assert early.json()["detail"] == "ยังไม่ถึงวันนัด ปิดงานล่วงหน้าไม่ได้"
    # ลูกค้าต้องไม่ได้รับแจ้งเตือน "งานเสร็จแล้ว" ก่อนเวลา
    assert all(n["kind"] != "service.completed"
               for n in client.get("/api/notifications", headers=headers).json()["items"])

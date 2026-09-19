"""เทสต์ integration ครบ 7 ขั้นตอนของ User Journey ผ่าน REST API + ฐานข้อมูลจริง
(SQLite ชั่วคราว หรือ PostgreSQL เมื่อตั้ง TEST_DATABASE_URL — ดู conftest.py)

รันด้วย:  cd backend && pytest -q
รับรู้ → ค้นหา → รายละเอียด → จองทดลองขับ → ซื้อออนไลน์ (+อัปโหลดเอกสาร/สินเชื่อ) → ติดตามสถานะ/แจ้งเตือน → หลังการขาย
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import loans

client = TestClient(app)

TOMORROW = (date.today() + timedelta(days=1)).isoformat()
PDF = b"%PDF-1.4\n% test document\n"


def register(username: str) -> dict:
    res = client.post("/api/register", json={
        "username": username,
        "password": "journey123",
        "full_name": "ทดสอบ เส้นทางลูกค้า",
        "email": f"{username}@example.com",
        "phone": "0812223333",
    })
    assert res.status_code == 201, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def free_slot(showroom_id: str) -> str:
    slots = client.get(f"/api/showrooms/{showroom_id}/slots", params={"date": TOMORROW}).json()["slots"]
    return next(s["time"] for s in slots if s["available"])


def reserve(headers: dict, car_id: str = "porsche-911", color_id: str = "guards-red") -> dict:
    res = client.post("/api/reservations", headers=headers, json={
        "car_id": car_id, "color_id": color_id, "option_ids": [],
        "name": "ทดสอบ เส้นทางลูกค้า", "phone": "0812223333", "email": "journey@example.com",
        "payment_method": "promptpay",
    })
    assert res.status_code == 201, res.text
    return res.json()


# ---------- ขั้นตอน 1-3: รับรู้ / ค้นหา / รายละเอียด ----------

def test_search_filter_and_sort():
    everything = client.get("/api/cars").json()
    assert len(everything) == 4
    assert all("rating" in c and "brand" in c for c in everything)

    awd = client.get("/api/cars", params={"drive": "awd"}).json()
    assert {c["id"] for c in awd} == {"gtr-r35", "huracan-evo"}

    cheap = client.get("/api/cars", params={"max_price": 15_000_000, "sort": "price_desc"}).json()
    prices = [c["price"] for c in cheap]
    assert prices == sorted(prices, reverse=True) and max(prices) <= 15_000_000

    assert [c["id"] for c in client.get("/api/cars", params={"q": "ferrari"}).json()] == ["ferrari-488"]
    assert client.get("/api/cars", params={"sort": "แปลก"}).status_code == 400

    facets = client.get("/api/cars/facets").json()
    assert "Porsche" in facets["brands"] and facets["price"]["min"] < facets["price"]["max"]


def test_promotions_hide_expired_by_default():
    active = client.get("/api/promotions").json()
    assert active and all(p["active"] for p in active)
    everything = client.get("/api/promotions", params={"include_expired": True}).json()
    assert any(not p["active"] for p in everything)   # GT-R หมดโปรฯ แล้ว (edge case)


# ---------- ขั้นตอน 4: จองทดลองขับ (คิวว่างเรียลไทม์) ----------

def test_booked_slot_disappears_and_double_booking_is_blocked():
    headers = register("tdriver1")
    time = free_slot("bangna")
    body = {"car_id": "gtr-r35", "showroom_id": "bangna", "date": TOMORROW, "time": time,
            "name": "ทดสอบ ทดลองขับ", "phone": "0812223333", "has_license": True}

    first = client.post("/api/testdrives", json=body, headers=headers)
    assert first.status_code == 201, first.text

    slots = client.get("/api/showrooms/bangna/slots", params={"date": TOMORROW}).json()["slots"]
    assert next(s for s in slots if s["time"] == time)["available"] is False
    assert client.post("/api/testdrives", json=body).status_code == 409   # ลูกค้าคนอื่นจองซ้ำไม่ได้

    # ยกเลิกแล้วคิวกลับมาว่าง
    code = first.json()["code"]
    assert client.post(f"/api/testdrives/{code}/cancel", headers=headers).json()["status"] == "cancelled"
    slots = client.get("/api/showrooms/bangna/slots", params={"date": TOMORROW}).json()["slots"]
    assert next(s for s in slots if s["time"] == time)["available"] is True


def test_guest_can_book_but_member_booking_is_private():
    headers = register("tdriver2")
    time = free_slot("rama3")
    body = {"car_id": "ferrari-488", "showroom_id": "rama3", "date": TOMORROW, "time": time,
            "name": "สมาชิก ส่วนตัว", "phone": "0812223333", "has_license": True}
    code = client.post("/api/testdrives", json=body, headers=headers).json()["code"]
    assert client.get(f"/api/testdrives/{code}").status_code == 404          # คนอื่นเปิดดูไม่ได้
    assert client.get(f"/api/testdrives/{code}", headers=headers).status_code == 200


# ---------- ขั้นตอน 5-6: ซื้อออนไลน์ + ติดตามสถานะ + แจ้งเตือน ----------

def test_full_purchase_flow_with_documents_loan_and_notifications(monkeypatch):
    headers = register("buyer01")

    assert client.post("/api/reservations", json={}).status_code in (401, 422)
    rsv = reserve(headers)
    assert rsv["code"].startswith("ADR-") and rsv["promotion"]     # โปรฯ ยังไม่หมดอายุถูกล็อกไว้

    # คนอื่นเห็น/ยกเลิกใบจองนี้ไม่ได้
    stranger = register("stranger1")
    assert client.get(f"/api/reservations/{rsv['code']}", headers=stranger).status_code == 404
    assert client.post(f"/api/reservations/{rsv['code']}/cancel", headers=stranger).status_code == 404

    # อัปโหลดเอกสาร — ไฟล์ปลอมนามสกุล .pdf ถูกปฏิเสธ
    fake = client.post("/api/documents", headers=headers, data={"kind": "id_card"},
                       files={"file": ("idcard.pdf", b"MZ\x90\x00 not a pdf", "application/pdf")})
    assert fake.status_code == 415
    doc = client.post("/api/documents", headers=headers, data={"kind": "id_card"},
                      files={"file": ("idcard.pdf", PDF, "application/pdf")})
    assert doc.status_code == 201, doc.text

    loan_body = {
        "reservation_code": rsv["code"], "plan_id": "krungthai-leasing",
        "down_payment": round(rsv["total_price"] * 0.3), "term_months": 60,
        "name": "ทดสอบ เส้นทางลูกค้า", "phone": "0812223333", "occupation": "เจ้าของกิจการ",
        "monthly_income": 2_000_000, "document_ids": [doc.json()["id"]], "consent_pdpa": True,
    }
    # ใช้เอกสารของคนอื่นแนบไม่ได้
    other_doc = client.post("/api/documents", headers=stranger, data={"kind": "income"},
                            files={"file": ("slip.pdf", PDF, "application/pdf")}).json()
    bad = dict(loan_body, document_ids=[other_doc["id"]])
    assert client.post("/api/loans", json=bad, headers=headers).status_code == 400

    loan = client.post("/api/loans", json=loan_body, headers=headers)
    assert loan.status_code == 201, loan.text
    assert loan.json()["status"] == "reviewing"
    assert loan.json()["documents"][0]["filename"] == "idcard.pdf"
    assert client.post("/api/loans", json=loan_body, headers=headers).status_code == 409  # ยื่นซ้อนไม่ได้

    # ยังไม่อนุมัติ -> นัดรับรถไม่ได้
    delivery = {"date": TOMORROW}
    assert client.post(f"/api/reservations/{rsv['code']}/delivery", json=delivery,
                       headers=headers).status_code == 400

    monkeypatch.setattr(loans, "REVIEW_SECONDS", 0)       # ข้ามเวลารอพิจารณา
    decided = client.get(f"/api/loans/{loan.json()['id']}", headers=headers).json()
    assert decided["status"] == "approved"

    done = client.post(f"/api/reservations/{rsv['code']}/delivery", json=delivery, headers=headers)
    assert done.status_code == 200 and done.json()["status"] == "delivery_scheduled"
    assert done.json()["delivery_documents"]

    mine = client.get("/api/me/bookings", headers=headers).json()
    assert mine["reservations"][0]["loan"]["status"] == "approved"

    feed = client.get("/api/notifications", headers=headers).json()
    kinds = [n["kind"] for n in feed["items"]]
    for expected in ("reservation.created", "loan.submitted", "loan.decided", "delivery.scheduled"):
        assert expected in kinds
    assert feed["unread"] >= 4
    assert client.post("/api/notifications/read-all", headers=headers).json()["unread"] == 0
    # แจ้งเตือนของตัวเองไม่รั่วไปหาคนอื่น
    assert all(n["kind"] != "loan.decided" for n in client.get("/api/notifications", headers=stranger).json()["items"])


def test_rejected_loan_offers_alternatives_and_allows_resubmit(monkeypatch):
    headers = register("buyer02")
    rsv = reserve(headers, "gtr-r35", "gun-metallic")
    body = {
        "reservation_code": rsv["code"], "plan_id": "scb-auto",
        "down_payment": round(rsv["total_price"] * 0.1), "term_months": 48,
        "name": "ทดสอบ เส้นทางลูกค้า", "phone": "0812223333", "occupation": "พนักงานบริษัท",
        "monthly_income": 18_000, "consent_pdpa": True,
    }
    loan_id = client.post("/api/loans", json=body, headers=headers).json()["id"]
    monkeypatch.setattr(loans, "REVIEW_SECONDS", 0)
    result = client.get(f"/api/loans/{loan_id}", headers=headers).json()
    assert result["status"] == "rejected"
    assert result["result"]["alternatives"]
    # ไม่ผ่านแล้วยื่นใหม่ได้
    assert client.post("/api/loans", json=dict(body, monthly_income=5_000_000), headers=headers).status_code == 201


def test_cancel_reservation_refunds_and_reverses_points():
    headers = register("buyer03")
    before = client.get("/api/loyalty", headers=headers).json()["balance"]
    rsv = reserve(headers)
    assert client.get("/api/loyalty", headers=headers).json()["balance"] == before + 2000
    cancelled = client.post(f"/api/reservations/{rsv['code']}/cancel", headers=headers).json()
    assert cancelled["status"] == "cancelled" and cancelled["refund"]["full_refund"] is True
    assert client.get("/api/loyalty", headers=headers).json()["balance"] == before


# ---------- ขั้นตอน 7: หลังการขาย ----------

def test_review_rating_and_verified_badge():
    headers = register("reviewer1")
    reserve(headers, "huracan-evo", "verde-mantis")
    body = {"car_id": "huracan-evo", "rating": 5, "title": "แรงสะใจ",
            "comment": "ขับในเมืองได้ดีกว่าที่คิด ระบบยกหน้าช่วยเรื่องลูกระนาดได้มาก"}
    res = client.post("/api/reviews", json=body, headers=headers)
    assert res.status_code == 201, res.text
    assert res.json()["verified"] is True
    assert res.json()["author"] == "ทดสอบ เ."                     # ปิดนามสกุล
    assert client.post("/api/reviews", json=body, headers=headers).status_code == 409

    car = client.get("/api/cars/huracan-evo").json()
    assert car["rating"]["count"] >= 1 and car["rating"]["avg"] is not None
    assert client.post("/api/reviews", json=dict(body, rating=9), headers=headers).status_code == 422
    assert client.post("/api/reviews", json=body).status_code == 401


def test_service_appointment_capacity_and_points_redeem():
    headers = register("owner001")
    types = client.get("/api/service/types").json()
    assert any(t["id"] == "periodic" for t in types)

    # สาขารังสิตไม่มีศูนย์บริการ
    assert client.get("/api/service/slots", params={"showroom_id": "rangsit", "date": TOMORROW}).status_code == 400

    body = {"car_id": "porsche-911", "showroom_id": "chiangmai", "date": TOMORROW, "time": "08:30",
            "service_type": "periodic", "mileage_km": 15000}
    first = client.post("/api/service/appointments", json=body, headers=headers)
    assert first.status_code == 201, first.text
    second_owner = register("owner002")
    assert client.post("/api/service/appointments", json=body, headers=second_owner).status_code == 201
    # ช่องซ่อม 2 ช่องเต็มแล้ว
    third = register("owner003")
    assert client.post("/api/service/appointments", json=body, headers=third).status_code == 409
    slot = next(s for s in client.get("/api/service/slots",
                params={"showroom_id": "chiangmai", "date": TOMORROW}).json()["slots"] if s["time"] == "08:30")
    assert slot["available"] is False and slot["remaining"] == 0

    # ได้คะแนนจากการจอง + นัดศูนย์ แล้วแลกของรางวัลได้
    reserve(headers)
    wallet = client.get("/api/loyalty", headers=headers).json()
    assert wallet["balance"] == 2100 and wallet["tier"]["id"] == "silver"
    assert client.post("/api/loyalty/redeem", json={"reward_id": "track-day"}, headers=headers).status_code == 400
    ok = client.post("/api/loyalty/redeem", json={"reward_id": "oil-change"}, headers=headers)
    assert ok.status_code == 200 and ok.json()["balance"] == 1300

    # ยกเลิกนัด -> หักคะแนนคืน และคิวว่างอีกครั้ง
    code = first.json()["code"]
    assert client.post(f"/api/service/appointments/{code}/cancel", headers=headers).json()["status"] == "cancelled"
    assert client.get("/api/loyalty", headers=headers).json()["balance"] == 1200
    assert client.post("/api/service/appointments", json=body, headers=third).status_code == 201


@pytest.mark.parametrize("path", ["/api/me/bookings", "/api/notifications", "/api/loyalty", "/api/documents"])
def test_member_endpoints_require_login(path):
    assert client.get(path).status_code == 401


def test_health_reports_database():
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["database"] in ("sqlite", "postgresql")

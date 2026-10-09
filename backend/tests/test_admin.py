"""เทสต์หลังบ้านสำหรับพนักงานโชว์รูม (/api/admin/*)

รันด้วย:  cd backend && pytest -q
ครอบคลุม: สิทธิ์ (customer 403 / ไม่มี token 401), ตัวเลขสรุป, ตัวกรอง + แบ่งหน้า,
การปิดงาน (มาแล้ว / ไม่มาตามนัด / ปิดงานบริการ) รวมทั้ง edge case วันที่ยังไม่ถึงและรหัสที่ไม่มีจริง
"""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import models
from app.database import engine
from app.main import app
from app.routers.after_sales import _service_load
from app.routers.showrooms import booked_times

client = TestClient(app)

TOMORROW = (date.today() + timedelta(days=1)).isoformat()
ADMIN = {"username": "admin", "password": "admin1234"}
CUSTOMER = {"username": "somchai", "password": "somchai123"}

# เส้นทางอ่านข้อมูล + เส้นทางปิดงาน (ใช้รหัสมั่วได้ เพราะสิทธิ์ถูกตรวจก่อนถึง handler)
READ_PATHS = [
    "/api/admin/overview",
    "/api/admin/testdrives",
    "/api/admin/reservations",
    "/api/admin/loans",
    "/api/admin/service-appointments",
]
WRITE_PATHS = [
    "/api/admin/testdrives/TD-0000-000000/complete",
    "/api/admin/service-appointments/SV-0000-000000/complete",
]


def auth_header(credentials: dict) -> dict:
    res = client.post("/api/login", json=credentials)
    assert res.status_code == 200, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def register(username: str, phone: str = "0899990000") -> dict:
    res = client.post("/api/register", json={
        "username": username,
        "password": "backoffice123",
        "full_name": "ทดสอบ หลังบ้าน",
        "email": f"{username}@example.com",
        "phone": phone,
    })
    assert res.status_code == 201, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def free_slot(showroom_id: str, taken: set[str] | None = None) -> str:
    slots = client.get(f"/api/showrooms/{showroom_id}/slots", params={"date": TOMORROW}).json()["slots"]
    return next(s["time"] for s in slots if s["available"] and s["time"] not in (taken or set()))


def book_testdrive(headers: dict, showroom_id: str, phone: str, taken: set[str]) -> dict:
    time = free_slot(showroom_id, taken)
    taken.add(time)
    res = client.post("/api/testdrives", headers=headers, json={
        "car_id": "gtr-r35", "showroom_id": showroom_id, "date": TOMORROW, "time": time,
        "name": "ทดสอบ หลังบ้าน", "phone": phone, "has_license": True,
    })
    assert res.status_code == 201, res.text
    return res.json()


def backdate(code: str, day: date) -> None:
    """เลื่อนวันนัดย้อนหลังตรงฐานข้อมูล — API ฝั่งลูกค้าจองย้อนหลังไม่ได้ จึงสร้างสถานะ "ถึงวันนัดแล้ว" แบบนี้"""
    with Session(engine) as db:
        record = db.get(models.TestDrive, code)
        record.date = day
        db.add(record)
        db.commit()


# ---------- 1. สิทธิ์เข้าถึง ----------

@pytest.mark.parametrize("path", READ_PATHS)
def test_read_endpoints_require_admin(path):
    assert client.get(path).status_code == 401                              # ไม่มี token
    assert client.get(path, headers=auth_header(CUSTOMER)).status_code == 403


@pytest.mark.parametrize("path", WRITE_PATHS)
def test_write_endpoints_require_admin(path):
    assert client.post(path).status_code == 401
    assert client.post(path, headers=auth_header(CUSTOMER)).status_code == 403


# ---------- 2. ตัวเลขสรุป ----------

def test_overview_numbers_follow_new_records():
    admin = auth_header(ADMIN)
    before = client.get("/api/admin/overview", headers=admin).json()

    headers = register("backoffice01")
    book_testdrive(headers, "chiangmai", "0899990001", set())
    rsv = client.post("/api/reservations", headers=headers, json={
        "car_id": "porsche-911", "color_id": "guards-red", "option_ids": [],
        "name": "ทดสอบ หลังบ้าน", "phone": "0899990001", "email": "backoffice01@example.com",
        "payment_method": "promptpay",
    })
    assert rsv.status_code == 201, rsv.text

    after = client.get("/api/admin/overview", headers=admin).json()
    assert after["members"]["total"] == before["members"]["total"] + 1
    assert after["testdrives"]["upcoming"] == before["testdrives"]["upcoming"] + 1
    assert after["reservations"]["by_status"]["reserved"] == \
        before["reservations"]["by_status"].get("reserved", 0) + 1
    assert after["reservations"]["active_value"] == \
        before["reservations"]["active_value"] + rsv.json()["total_price"]
    assert after["reservations"]["booking_fee_received"] > before["reservations"]["booking_fee_received"]


# ---------- 3. ตัวกรอง + แบ่งหน้า ----------

def test_testdrive_filters_and_pagination():
    admin = auth_header(ADMIN)
    headers = register("backoffice02", "0877770002")
    phone = "0877770002"
    taken: set[str] = set()
    codes = [book_testdrive(headers, "rama3", phone, taken)["code"] for _ in range(3)]

    # ค้นหาด้วยเบอร์โทรเฉพาะของเทสต์นี้ ทำให้ยอดรวมแน่นอนไม่ปนกับเทสต์อื่น
    page1 = client.get("/api/admin/testdrives", headers=admin,
                       params={"q": phone, "per_page": 2}).json()
    assert page1["total"] == 3 and page1["total_pages"] == 2 and len(page1["items"]) == 2
    assert page1["page"] == 1 and page1["per_page"] == 2

    page2 = client.get("/api/admin/testdrives", headers=admin,
                       params={"q": phone, "per_page": 2, "page": 2}).json()
    assert len(page2["items"]) == 1
    assert {i["code"] for i in page1["items"] + page2["items"]} == set(codes)

    # เรียงตามวัน-เวลา และกรองได้ด้วยสถานะ/สาขา/ช่วงวันที่
    times = [i["time"] for i in page1["items"]]
    assert times == sorted(times)
    assert client.get("/api/admin/testdrives", headers=admin,
                      params={"q": phone, "status": "cancelled"}).json()["total"] == 0
    assert client.get("/api/admin/testdrives", headers=admin,
                      params={"q": phone, "showroom_id": "bangna"}).json()["total"] == 0
    assert client.get("/api/admin/testdrives", headers=admin,
                      params={"q": phone, "date_from": TOMORROW, "date_to": TOMORROW}).json()["total"] == 3
    assert client.get("/api/admin/testdrives", headers=admin,
                      params={"date_from": "เมื่อวาน"}).status_code == 400
    assert client.get("/api/admin/testdrives", headers=admin,
                      params={"status": "แปลก"}).status_code == 400
    assert client.get("/api/admin/testdrives", headers=admin,
                      params={"q": codes[0]}).json()["total"] == 1


def test_reservation_and_loan_lists_show_loan_status():
    admin = auth_header(ADMIN)
    headers = register("backoffice03", "0866660003")
    rsv = client.post("/api/reservations", headers=headers, json={
        "car_id": "ferrari-488", "color_id": "rosso-corsa", "option_ids": [],
        "name": "ทดสอบ สินเชื่อ", "phone": "0866660003", "email": "backoffice03@example.com",
        "payment_method": "card",
    })
    assert rsv.status_code == 201, rsv.text
    code = rsv.json()["code"]

    found = client.get("/api/admin/reservations", headers=admin, params={"q": code}).json()
    assert found["total"] == 1
    assert found["items"][0]["loan_status"] is None          # ยังไม่ได้ยื่นสินเชื่อ

    loan = client.post("/api/loans", headers=headers, json={
        "reservation_code": code, "plan_id": "krungthai-leasing", "down_payment": 5_000_000,
        "term_months": 48, "name": "ทดสอบ สินเชื่อ", "phone": "0866660003",
        "occupation": "พนักงานบริษัท", "monthly_income": 900_000, "consent_pdpa": True,
    })
    assert loan.status_code == 201, loan.text

    with_loan = client.get("/api/admin/reservations", headers=admin, params={"q": code}).json()
    assert with_loan["items"][0]["loan_status"] in ("reviewing", "approved", "rejected")

    loans = client.get("/api/admin/loans", headers=admin, params={"q": code}).json()
    assert loans["total"] == 1 and loans["items"][0]["reservation_code"] == code
    assert client.get("/api/admin/loans", headers=admin,
                      params={"q": code, "status": "approved"}).json()["total"] in (0, 1)
    assert client.get("/api/admin/loans", headers=admin, params={"status": "แปลก"}).status_code == 400


def test_service_appointment_filters():
    admin = auth_header(ADMIN)
    headers = register("backoffice04", "0855550004")
    booked = client.post("/api/service/appointments", headers=headers, json={
        "car_id": "gtr-r35", "showroom_id": "bangna", "date": TOMORROW,
        "time": "13:30", "service_type": "periodic", "mileage_km": 12000, "note": "",
    })
    assert booked.status_code == 201, booked.text

    listing = client.get("/api/admin/service-appointments", headers=admin,
                         params={"showroom_id": "bangna", "date_from": TOMORROW,
                                 "date_to": TOMORROW, "status": "booked"}).json()
    assert booked.json()["code"] in {i["code"] for i in listing["items"]}
    assert client.get("/api/admin/service-appointments", headers=admin,
                      params={"status": "แปลก"}).status_code == 400
    assert client.get("/api/admin/service-appointments", headers=admin,
                      params={"date_to": "พรุ่งนี้"}).status_code == 400


# ---------- 4. ปิดงานหน้าเคาน์เตอร์ ----------

def test_complete_testdrive_notifies_customer_and_frees_slot():
    admin = auth_header(ADMIN)
    headers = register("backoffice05", "0844440005")
    taken: set[str] = set()
    record = book_testdrive(headers, "bangna", "0844440005", taken)
    future = book_testdrive(headers, "bangna", "0844440005", taken)

    # ยังไม่ถึงวันนัด ปิดงานไม่ได้ + รหัสที่ไม่มีจริงตอบ 404
    assert client.post(f"/api/admin/testdrives/{future['code']}/complete",
                       headers=admin).status_code == 400
    assert client.post("/api/admin/testdrives/TD-9999-ZZZZZZ/complete",
                       headers=admin).status_code == 404

    backdate(record["code"], date.today())
    done = client.post(f"/api/admin/testdrives/{record['code']}/complete", headers=admin)
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"

    # ปิดซ้ำไม่ได้ (สถานะไม่ใช่ confirmed แล้ว)
    assert client.post(f"/api/admin/testdrives/{record['code']}/complete",
                       headers=admin).status_code == 400

    feed = client.get("/api/notifications", headers=headers).json()["items"]
    thanks = next(n for n in feed if n["kind"] == "testdrive.completed")
    assert "200" in thanks["message"] and thanks["link"] == "/pages/after-sales.html#reviews"

    # นัดที่ปิดงานแล้วต้องไม่กินคิวของวันนั้นต่อ (booked_times นับเฉพาะ confirmed)
    with Session(engine) as db:
        assert record["time"] not in booked_times(db, "bangna", date.today())

    listing = client.get("/api/admin/testdrives", headers=admin,
                         params={"q": record["code"], "status": "completed"}).json()
    assert listing["total"] == 1


def test_no_show_marks_absent_without_thank_you_notification():
    admin = auth_header(ADMIN)
    headers = register("backoffice06", "0833330006")
    record = book_testdrive(headers, "rangsit", "0833330006", set())
    backdate(record["code"], date.today() - timedelta(days=1))

    res = client.post(f"/api/admin/testdrives/{record['code']}/complete",
                      headers=admin, params={"outcome": "no_show"})
    assert res.status_code == 200 and res.json()["status"] == "no_show"

    feed = client.get("/api/notifications", headers=headers).json()["items"]
    assert all(n["kind"] != "testdrive.completed" for n in feed)
    assert client.post(f"/api/admin/testdrives/{record['code']}/complete",
                       headers=admin, params={"outcome": "แปลก"}).status_code == 400


def test_complete_service_appointment_frees_capacity_and_notifies():
    admin = auth_header(ADMIN)
    headers = register("backoffice07", "0822220007")
    booked = client.post("/api/service/appointments", headers=headers, json={
        "car_id": "porsche-911", "showroom_id": "rama3", "date": TOMORROW,
        "time": "16:30", "service_type": "periodic", "mileage_km": 30000, "note": "",
    })
    assert booked.status_code == 201, booked.text
    code = booked.json()["code"]
    day = date.fromisoformat(TOMORROW)

    with Session(engine) as db:
        before = _service_load(db, "rama3", day).get("16:30", 0)
    assert before >= 1

    done = client.post(f"/api/admin/service-appointments/{code}/complete", headers=admin)
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"

    # งานที่ปิดแล้วต้องไม่กินช่องซ่อมของวันนั้น (_service_load นับเฉพาะ booked)
    with Session(engine) as db:
        assert _service_load(db, "rama3", day).get("16:30", 0) == before - 1

    feed = client.get("/api/notifications", headers=headers).json()["items"]
    assert any(n["kind"] == "service.completed" for n in feed)

    assert client.post(f"/api/admin/service-appointments/{code}/complete",
                       headers=admin).status_code == 400
    assert client.post("/api/admin/service-appointments/SV-9999-ZZZZZZ/complete",
                       headers=admin).status_code == 404

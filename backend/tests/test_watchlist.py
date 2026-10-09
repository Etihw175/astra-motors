"""เทสต์รายการที่สนใจ (watchlist) + แจ้งเตือนโปรโมชั่นใกล้หมดอายุ (journey ขั้นที่ 1-2)

สิ่งที่ต้องกันไว้ให้ไม่พังในอนาคต:
- ปุ่มหัวใจกดซ้ำต้องไม่เป็น error (idempotent) และลบสิ่งที่ไม่มีก็ต้องไม่เป็น error
- รายการของแต่ละคนต้องไม่ปนกัน (ข้อมูลส่วนตัว)
- แจ้งเตือน promo.ending เกิดครั้งเดียวต่อโปรฯ 1 รอบ แม้จะเปิดกล่องแจ้งเตือนหลายครั้ง
  (ไม่งั้นลูกค้าจะโดนสแปมทุกครั้งที่เปิดหน้าเว็บ)
"""
from datetime import date, timedelta

from fastapi.testclient import TestClient
import pytest
from sqlmodel import Session, select

from app.database import engine
from app.main import app
from app.models import Car

client = TestClient(app)


def register(username: str) -> dict:
    res = client.post("/api/register", json={
        "username": username,
        "password": "watch12345",
        "full_name": "ทดสอบ รายการที่สนใจ",
        "email": f"{username}@example.com",
        "phone": "0812223333",
    })
    assert res.status_code == 201, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def set_promo_expiry(car_id: str, days_from_today: int) -> str:
    """ตั้งวันหมดอายุโปรฯ ของรถในฐานข้อมูลเทสต์ให้ใกล้หมด แล้วคืนวันที่ที่ตั้งไว้"""
    expires = (date.today() + timedelta(days=days_from_today)).isoformat()
    with Session(engine) as db:
        car = db.get(Car, car_id)
        car.promotion = {"title": "โปรฯ ทดสอบใกล้หมด", "expires": expires}
        db.add(car)
        db.commit()
    return expires


@pytest.fixture(autouse=True)
def restore_promotions():
    """คืนค่าโปรโมชั่นเดิมหลังเทสต์จบ — ตาราง cars ใช้ร่วมกับไฟล์เทสต์อื่น ปล่อยค่าที่แก้ไว้จะทำให้ไฟล์อื่นพัง"""
    with Session(engine) as db:
        before = {car.id: car.promotion for car in db.exec(select(Car)).all()}
    yield
    with Session(engine) as db:
        for car_id, promotion in before.items():
            car = db.get(Car, car_id)
            car.promotion = promotion
            db.add(car)
        db.commit()


def promo_alerts(headers: dict) -> list[dict]:
    """เปิดกล่องแจ้งเตือน (จุดที่ระบบเช็คโปรฯ ใกล้หมด) แล้วคืนเฉพาะแจ้งเตือนชนิด promo.ending"""
    items = client.get("/api/notifications", headers=headers, params={"limit": 100}).json()["items"]
    return [n for n in items if n["kind"] == "promo.ending"]


# ---------- สิทธิ์การเข้าถึง ----------

def test_watchlist_requires_login():
    assert client.get("/api/watchlist").status_code == 401
    assert client.get("/api/watchlist/ids").status_code == 401
    assert client.post("/api/watchlist", json={"car_id": "porsche-911"}).status_code == 401
    assert client.delete("/api/watchlist/porsche-911").status_code == 401


# ---------- เพิ่ม / เพิ่มซ้ำ / ลบ ----------

def test_add_twice_is_idempotent_then_remove():
    headers = register("watcher1")
    assert client.get("/api/watchlist", headers=headers).json() == []

    first = client.post("/api/watchlist", json={"car_id": "porsche-911"}, headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["watching"] is True

    # กดหัวใจซ้ำ (กดสลับไปมา/เปิดสองแท็บ) ต้องได้ 200 ไม่ใช่ 409 และไม่เกิดแถวที่สอง
    again = client.post("/api/watchlist", json={"car_id": "porsche-911"}, headers=headers)
    assert again.status_code == 200, again.text
    assert client.get("/api/watchlist/ids", headers=headers).json() == ["porsche-911"]

    items = client.get("/api/watchlist", headers=headers).json()
    assert len(items) == 1
    assert items[0]["car"]["name"] and "rating" in items[0]["car"]        # ใช้ car_dict + rating_map
    assert set(items[0]["promotion"]) >= {"days_left", "active", "expires"}

    assert client.delete("/api/watchlist/porsche-911", headers=headers).status_code == 204
    assert client.get("/api/watchlist/ids", headers=headers).json() == []
    # ลบสิ่งที่ไม่มีอยู่แล้วก็ยังเป็น 204 — ปลายทางที่ต้องการ (ไม่อยู่ในรายการ) เป็นจริงอยู่แล้ว
    assert client.delete("/api/watchlist/porsche-911", headers=headers).status_code == 204


def test_unknown_car_is_404():
    headers = register("watcher2")
    assert client.post("/api/watchlist", json={"car_id": "ไม่มีรุ่นนี้"}, headers=headers).status_code == 404


def test_watchlists_are_private_per_user():
    mine = register("watcher3")
    other = register("watcher4")
    client.post("/api/watchlist", json={"car_id": "ferrari-488"}, headers=mine)
    client.post("/api/watchlist", json={"car_id": "gtr-r35"}, headers=other)

    assert client.get("/api/watchlist/ids", headers=mine).json() == ["ferrari-488"]
    assert client.get("/api/watchlist/ids", headers=other).json() == ["gtr-r35"]
    # ลบของคนอื่นไม่ได้ (เงียบ ๆ 204 แต่ของเขายังอยู่)
    assert client.delete("/api/watchlist/gtr-r35", headers=mine).status_code == 204
    assert client.get("/api/watchlist/ids", headers=other).json() == ["gtr-r35"]


# ---------- แจ้งเตือนโปรโมชั่นใกล้หมดอายุ ----------

def test_promo_ending_alert_fires_once_for_watched_car():
    headers = register("watcher5")
    expires = set_promo_expiry("huracan-evo", 2)        # เหลือ 2 วัน = ภายในเกณฑ์ ≤ 3 วัน
    client.post("/api/watchlist", json={"car_id": "huracan-evo"}, headers=headers)

    alerts = promo_alerts(headers)
    assert len(alerts) == 1, alerts
    assert "huracan-evo" in alerts[0]["link"] and expires in alerts[0]["link"]
    assert "เหลืออีก 2 วัน" in alerts[0]["message"]

    # เปิดกล่องแจ้งเตือนซ้ำ ๆ (รวมทางกระดิ่ง/unread-count) ต้องไม่แจ้งซ้ำ
    client.get("/api/notifications/unread-count", headers=headers)
    promo_alerts(headers)
    assert len(promo_alerts(headers)) == 1


def test_no_alert_for_car_not_on_watchlist_or_promo_far_away():
    headers = register("watcher6")
    set_promo_expiry("ferrari-488", 1)                  # โปรฯ ใกล้หมด แต่ไม่ได้ติดตามรุ่นนี้
    set_promo_expiry("porsche-911", 30)                 # ติดตาม แต่โปรฯ ยังอีกไกล
    client.post("/api/watchlist", json={"car_id": "porsche-911"}, headers=headers)

    assert promo_alerts(headers) == []

    # เลื่อนวันหมดอายุของรุ่นที่ติดตามให้เข้าเกณฑ์ แล้วต้องแจ้งเตือนรอบใหม่
    set_promo_expiry("porsche-911", 0)                  # หมดวันนี้
    alerts = promo_alerts(headers)
    assert len(alerts) == 1
    assert "หมดวันนี้" in alerts[0]["message"]


def test_expired_promo_does_not_alert():
    headers = register("watcher7")
    set_promo_expiry("gtr-r35", -1)                     # หมดอายุไปแล้วเมื่อวาน — เตือนไม่ทันแล้ว
    client.post("/api/watchlist", json={"car_id": "gtr-r35"}, headers=headers)
    assert promo_alerts(headers) == []

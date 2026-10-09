"""เทสต์แจ้งเตือนแบบเรียลไทม์ (Server-Sent Events) — ตั๋วเปิดสตรีม + ตัวสตรีมเอง + fallback แบบ poll

สตรีมจริงจะวนไม่จบ จึงเปิดด้วย max_events (พารามิเตอร์ภายในสำหรับเทสต์) เพื่อให้จบเองแน่นอน
"""
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def register(username: str) -> dict:
    res = client.post("/api/register", json={
        "username": username,
        "password": "realtime123",
        "full_name": "ทดสอบ เรียลไทม์",
        "email": f"{username}@example.com",
        "phone": "0812224444",
    })
    assert res.status_code == 201, res.text
    return {"Authorization": "Bearer " + res.json()["access_token"]}


def test_stream_ticket_requires_login():
    assert client.post("/api/notifications/stream-ticket").status_code == 401


def test_fake_or_used_ticket_is_rejected():
    headers = register("rt_ticket")

    # ตั๋วปลอม
    bad = client.get("/api/notifications/stream", params={"ticket": "ไม่ใช่ตั๋วจริง", "max_events": 1})
    assert bad.status_code == 401
    assert "ตั๋ว" in bad.json()["detail"]

    # ตั๋วจริงใช้ได้ครั้งเดียว — รอบที่สองต้องถูกปฏิเสธ
    ticket = client.post("/api/notifications/stream-ticket", headers=headers).json()["ticket"]
    with client.stream("GET", "/api/notifications/stream",
                       params={"ticket": ticket, "max_events": 1}) as first:
        assert first.status_code == 200
    again = client.get("/api/notifications/stream", params={"ticket": ticket, "max_events": 1})
    assert again.status_code == 401


def test_stream_sends_unread_event_first():
    headers = register("rt_stream")
    body = client.post("/api/notifications/stream-ticket", headers=headers).json()
    assert body["expires_in"] == 30

    with client.stream("GET", "/api/notifications/stream",
                       params={"ticket": body["ticket"], "max_events": 1}) as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        assert res.headers["cache-control"] == "no-cache"
        assert res.headers["x-accel-buffering"] == "no"
        lines = [line for line in res.iter_lines() if line]
        assert lines[0] == "event: unread"
        assert lines[1].startswith("data: ")
        assert '"unread"' in lines[1]


def test_poll_endpoints_still_work_as_fallback():
    headers = register("rt_fallback")
    assert client.get("/api/notifications/unread-count", headers=headers).json()["unread"] == 0

    showroom = client.get("/api/showrooms").json()[0]["id"]
    slots = client.get(f"/api/showrooms/{showroom}/slots", params={"date": TOMORROW}).json()["slots"]
    booked = client.post("/api/testdrives", headers=headers, json={
        "car_id": "porsche-911", "showroom_id": showroom, "date": TOMORROW,
        "time": next(s["time"] for s in slots if s["available"]),
        "name": "ทดสอบ เรียลไทม์", "phone": "0812224444", "email": "rt_fallback@example.com", "has_license": True,
    })
    assert booked.status_code == 201, booked.text

    assert client.get("/api/notifications/unread-count", headers=headers).json()["unread"] == 1
    listed = client.get("/api/notifications", headers=headers).json()
    assert listed["unread"] == 1 and listed["items"][0]["kind"] == "testdrive.booked"

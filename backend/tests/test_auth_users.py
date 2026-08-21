"""เทสต์ REST API ระบบสมาชิก + จัดการผู้ใช้

รันด้วย:  cd backend && pytest -q
ครอบคลุมทั้ง happy path และ error case ตามที่เอกสารเวิร์กชอปกำหนด
(ทุก endpoint ที่แก้ไข/ลบข้อมูล ต้องตรวจสอบสิทธิ์ ไม่ใช่แค่ happy path)
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

client = TestClient(app)

ADMIN = {"username": "admin", "password": "admin1234"}
CUSTOMER = {"username": "somchai", "password": "somchai123"}


def auth_header(credentials: dict) -> dict:
    res = client.post("/api/login", json=credentials)
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": "Bearer " + token}


# ---------- 1. Authentication ----------

def test_register_success_and_duplicate_username():
    body = {
        "username": "testuser1",
        "password": "test1234",
        "full_name": "ผู้ใช้ทดสอบ หนึ่ง",
        "email": "testuser1@example.com",
        "phone": "0811111111",
    }
    res = client.post("/api/register", json=body)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["user"]["username"] == "testuser1"
    assert data["user"]["role"] == "customer"      # สมัครเองต้องไม่ได้เป็น admin
    assert "password" not in data["user"]           # ห้ามส่งรหัสผ่านกลับ
    assert "password_hash" not in data["user"]

    # สมัครซ้ำด้วย username เดิม -> 409
    duplicate = dict(body, email="other@example.com")
    assert client.post("/api/register", json=duplicate).status_code == 409


def test_register_rejects_weak_password_and_bad_username():
    weak = {
        "username": "weakpass",
        "password": "abcdefgh",   # ไม่มีตัวเลข
        "full_name": "รหัสอ่อน ทดสอบ",
        "email": "weak@example.com",
        "phone": "0822222222",
    }
    assert client.post("/api/register", json=weak).status_code == 400

    bad_name = dict(weak, username="ab", password="abcd1234", email="b@example.com")
    assert client.post("/api/register", json=bad_name).status_code == 422   # Pydantic min_length

    bad_email = dict(weak, username="okname1", password="abcd1234", email="not-an-email")
    assert client.post("/api/register", json=bad_email).status_code == 422


def test_login_success_and_wrong_password():
    res = client.post("/api/login", json=CUSTOMER)
    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"

    bad = client.post("/api/login", json={"username": "somchai", "password": "wrong-pass"})
    assert bad.status_code == 401
    # ข้อความต้องไม่บอกว่ามี username นี้อยู่จริงหรือไม่ (กัน user enumeration)
    assert bad.json()["detail"] == "username หรือรหัสผ่านไม่ถูกต้อง"


def test_login_with_email_works():
    res = client.post("/api/login", json={"username": "somchai@example.com", "password": "somchai123"})
    assert res.status_code == 200


def test_logout_invalidates_token():
    headers = auth_header(CUSTOMER)
    assert client.get("/api/me", headers=headers).status_code == 200
    assert client.post("/api/logout", headers=headers).status_code == 200
    assert client.get("/api/me", headers=headers).status_code == 401


def test_change_password_flow():
    client.post("/api/register", json={
        "username": "pwuser",
        "password": "first1234",
        "full_name": "เปลี่ยนรหัส ทดสอบ",
        "email": "pwuser@example.com",
        "phone": "0833333333",
    })
    headers = auth_header({"username": "pwuser", "password": "first1234"})

    wrong = client.post("/api/change-password", headers=headers,
                        json={"current_password": "nope1234", "new_password": "second1234"})
    assert wrong.status_code == 400

    ok = client.post("/api/change-password", headers=headers,
                     json={"current_password": "first1234", "new_password": "second1234"})
    assert ok.status_code == 200

    # เปลี่ยนแล้ว token เดิมต้องใช้ไม่ได้ + ล็อกอินได้ด้วยรหัสใหม่เท่านั้น
    assert client.get("/api/me", headers=headers).status_code == 401
    assert client.post("/api/login", json={"username": "pwuser", "password": "first1234"}).status_code == 401
    assert client.post("/api/login", json={"username": "pwuser", "password": "second1234"}).status_code == 200


# ---------- 2. User Management ----------

def test_me_requires_token():
    assert client.get("/api/me").status_code == 401
    res = client.get("/api/me", headers=auth_header(ADMIN))
    assert res.status_code == 200
    assert res.json()["username"] == "admin"


def test_list_users_pagination_admin_only():
    assert client.get("/api/users", headers=auth_header(CUSTOMER)).status_code == 403

    res = client.get("/api/users?page=1&per_page=2", headers=auth_header(ADMIN))
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) <= 2
    assert body["page"] == 1 and body["per_page"] == 2
    assert body["total"] >= 3
    assert body["total_pages"] == max(1, -(-body["total"] // 2))

    # ค้นหา + กรองตามสิทธิ์
    filtered = client.get("/api/users?role=admin", headers=auth_header(ADMIN)).json()
    assert all(u["role"] == "admin" for u in filtered["items"])
    assert client.get("/api/users?per_page=999", headers=auth_header(ADMIN)).status_code == 422


def test_get_user_permission_rules():
    admin_headers = auth_header(ADMIN)
    customer_headers = auth_header(CUSTOMER)
    me = client.get("/api/me", headers=customer_headers).json()

    assert client.get("/api/users/" + str(me["id"]), headers=customer_headers).status_code == 200
    assert client.get("/api/users/1", headers=customer_headers).status_code == 403   # บัญชีของ admin
    assert client.get("/api/users/" + str(me["id"]), headers=admin_headers).status_code == 200
    assert client.get("/api/users/999999", headers=admin_headers).status_code == 404


def test_update_user_and_role_escalation_blocked():
    headers = auth_header(CUSTOMER)
    me = client.get("/api/me", headers=headers).json()
    path = "/api/users/" + str(me["id"])

    res = client.put(path, headers=headers, json={"phone": "0855555555"})
    assert res.status_code == 200
    assert res.json()["phone"] == "0855555555"

    # ผู้ใช้ทั่วไปยกระดับตัวเองเป็น admin ไม่ได้
    escalate = client.put(path, headers=headers, json={"role": "admin"})
    assert escalate.status_code == 403
    assert client.get("/api/me", headers=headers).json()["role"] == "customer"

    # แก้ข้อมูลของคนอื่นไม่ได้
    assert client.put("/api/users/1", headers=headers, json={"phone": "0866666666"}).status_code == 403


def test_delete_user_admin_only_and_not_self():
    created = client.post("/api/register", json={
        "username": "deleteme",
        "password": "delete1234",
        "full_name": "ลบทิ้ง ทดสอบ",
        "email": "deleteme@example.com",
        "phone": "0844444444",
    }).json()["user"]

    victim_headers = auth_header({"username": "deleteme", "password": "delete1234"})
    assert client.delete("/api/users/" + str(created["id"]), headers=victim_headers).status_code == 403

    admin_headers = auth_header(ADMIN)
    admin_id = client.get("/api/me", headers=admin_headers).json()["id"]
    assert client.delete("/api/users/" + str(admin_id), headers=admin_headers).status_code == 400

    assert client.delete("/api/users/" + str(created["id"]), headers=admin_headers).status_code == 204
    assert client.get("/api/users/" + str(created["id"]), headers=admin_headers).status_code == 404
    # token ของบัญชีที่ถูกลบต้องใช้ต่อไม่ได้
    assert client.get("/api/me", headers=victim_headers).status_code == 401


@pytest.mark.parametrize(
    "name,expected_available",
    [("admin", False), ("brand.new_1", True), ("ab", False)],
)
def test_check_username(name, expected_available):
    res = client.get("/api/check-username/" + name)
    assert res.status_code == 200
    assert res.json()["available"] is expected_available


def test_suspended_account_cannot_login():
    client.post("/api/register", json={
        "username": "banneduser",
        "password": "banned1234",
        "full_name": "ถูกระงับ ทดสอบ",
        "email": "banned@example.com",
        "phone": "0877777777",
    })
    victim = client.get("/api/users?q=banneduser", headers=auth_header(ADMIN)).json()["items"][0]

    res = client.put("/api/users/" + str(victim["id"]), headers=auth_header(ADMIN),
                     json={"is_active": False})
    assert res.status_code == 200 and res.json()["is_active"] is False
    assert client.post("/api/login", json={"username": "banneduser", "password": "banned1234"}).status_code == 403

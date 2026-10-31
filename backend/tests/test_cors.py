"""CORS เปิดเฉพาะตอนตั้ง env CORS_ORIGINS และเปิดให้เฉพาะโดเมนที่ระบุ

ใช้ตอนเอาหน้าเว็บไปวางคนละโฮสต์กับ API (ลากขึ้นโฮสต์ FTP แล้ว API อยู่ Render)
ต้อง import app ใหม่ในแต่ละเทสต์เพราะ middleware ถูกต่อตอนโหลดโมดูล ไม่ใช่ตอนรับ request
"""
import importlib
import sys

from fastapi.testclient import TestClient


def _reload_app(monkeypatch, origins: str | None):
    if origins is None:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ORIGINS", origins)
    sys.modules.pop("app.main", None)
    return importlib.import_module("app.main").app


def test_ไม่ตั้ง_env_แปลว่าไม่เปิด_cors(monkeypatch):
    client = TestClient(_reload_app(monkeypatch, None))
    res = client.get("/api/health", headers={"Origin": "https://astra.example.com"})
    assert res.status_code == 200
    assert "access-control-allow-origin" not in res.headers


def test_โดเมนที่ระบุไว้เรียกข้ามโฮสต์ได้(monkeypatch):
    client = TestClient(_reload_app(monkeypatch, "https://astra.example.com"))
    res = client.get("/api/health", headers={"Origin": "https://astra.example.com"})
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "https://astra.example.com"


def test_โดเมนอื่นยังโดนปิดอยู่(monkeypatch):
    client = TestClient(_reload_app(monkeypatch, "https://astra.example.com"))
    res = client.get("/api/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in res.headers


def test_preflight_ผ่าน_header_ที่หน้าเว็บใช้จริง(monkeypatch):
    client = TestClient(_reload_app(monkeypatch, "https://astra.example.com"))
    res = client.options(
        "/api/testdrives",
        headers={
            "Origin": "https://astra.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "https://astra.example.com"


def test_ปล่อยให้หน้าเว็บอ่าน_retry_after_ตอนโดน_429(monkeypatch):
    """หน้าเว็บอ่าน Retry-After เพื่อบอกผู้ใช้ว่าให้รอกี่วินาที ข้ามโดเมนต้อง expose ให้ด้วย"""
    client = TestClient(_reload_app(monkeypatch, "https://astra.example.com"))
    res = client.get("/api/health", headers={"Origin": "https://astra.example.com"})
    assert "Retry-After" in res.headers["access-control-expose-headers"]


def test_คืนสภาพโมดูลให้เทสต์อื่น(monkeypatch):
    """เทสต์ไฟล์อื่นใช้ app.main ตัวที่ไม่มี CORS ปิดท้ายด้วยการโหลดกลับเป็นค่าเริ่มต้น"""
    app = _reload_app(monkeypatch, None)
    assert app is not None

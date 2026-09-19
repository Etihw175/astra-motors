"""เทสต์ API จำลองการใช้งานบนถนนไทย (น้ำท่วม / ลูกระนาด / หลุมบ่อ / ฝน / ค่าน้ำมัน)

รันด้วย:  cd backend && pytest -q
"""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

client = TestClient(app)

BASE = {
    "car_id": "gtr-r35",
    "flood_depth_cm": 0,
    "bump_height_cm": 0,
    "road_rough": 0,
    "front_lift": False,
    "km_per_year": 12000,
    "traffic_share_pct": 60,
    "fuel_price": 41.5,
}


def simulate(**overrides):
    res = client.post("/api/simulation", json=dict(BASE, **overrides))
    assert res.status_code == 200, res.text
    return res.json()


def scenario(data, scenario_id):
    return next(s for s in data["scenarios"] if s["id"] == scenario_id)


def test_conditions_lists_presets():
    res = client.get("/api/simulation/conditions")
    assert res.status_code == 200
    body = res.json()
    assert {"floods", "bumps", "roads", "defaults"} <= set(body)
    assert any(f["depth_cm"] == 0 for f in body["floods"])
    assert body["defaults"]["fuel_price"] > 0


def test_dry_road_scores_well():
    data = simulate()
    assert scenario(data, "flood")["verdict"] == "ok"
    assert scenario(data, "bump")["verdict"] == "ok"
    assert data["score"]["total"] >= 60
    assert data["score"]["grade"]["letter"] in ("A", "B")


def test_deep_flood_is_refused():
    data = simulate(flood_depth_cm=40)
    flood = scenario(data, "flood")
    assert flood["verdict"] == "danger"
    assert "ห้ามฝ่า" in flood["headline"]
    # เตือนเรื่องน้ำเข้าเครื่อง ไม่ใช่แค่บอกว่าผ่านไม่ได้
    assert any("hydrolock" in a for a in flood["advice"])


def test_shallow_puddle_is_fine():
    assert scenario(simulate(flood_depth_cm=4), "flood")["verdict"] == "ok"


def test_bump_higher_than_clearance_is_danger():
    data = simulate(bump_height_cm=18)
    assert scenario(data, "bump")["verdict"] == "danger"


def test_front_lift_raises_clearance_when_car_has_it():
    without = simulate(car_id="huracan-evo", bump_height_cm=13)
    with_lift = simulate(car_id="huracan-evo", bump_height_cm=13, front_lift=True)

    assert with_lift["clearance"]["effective_mm"] == without["clearance"]["effective_mm"] + 45
    assert with_lift["clearance"]["front_lift_active"] is True
    assert scenario(with_lift, "bump")["score"] > scenario(without, "bump")["score"]


def test_front_lift_ignored_on_car_without_it():
    data = simulate(car_id="gtr-r35", front_lift=True)
    assert data["clearance"]["front_lift_available"] is False
    assert data["clearance"]["effective_mm"] == data["clearance"]["base_mm"]
    assert data["note"] and "ไม่มีระบบยกหน้ารถ" in data["note"]


def test_more_traffic_means_worse_fuel_economy():
    highway = scenario(simulate(traffic_share_pct=0), "fuel")["numbers"]
    jam = scenario(simulate(traffic_share_pct=100), "fuel")["numbers"]

    assert jam["blended_kmpl"] < highway["blended_kmpl"]
    assert jam["cost_per_year"] > highway["cost_per_year"]
    # วิ่งทางไกลล้วนต้องได้เท่าอัตราสิ้นเปลืองบนทางหลวงพอดี
    assert abs(highway["blended_kmpl"] - highway["highway_kmpl"]) < 0.05


def test_fuel_cost_scales_with_distance_and_price():
    cheap = scenario(simulate(km_per_year=10000, fuel_price=40), "fuel")["numbers"]
    pricey = scenario(simulate(km_per_year=20000, fuel_price=50), "fuel")["numbers"]
    assert pricey["cost_per_year"] > cheap["cost_per_year"] * 2


def test_rough_road_lowers_score():
    smooth = scenario(simulate(road_rough=0), "rough")["score"]
    broken = scenario(simulate(road_rough=3), "rough")["score"]
    assert broken < smooth


def test_ranking_covers_every_car_sorted_by_score():
    data = simulate(flood_depth_cm=12, bump_height_cm=12, front_lift=True)
    totals = [r["total"] for r in data["ranking"]]

    assert len(data["ranking"]) == 4
    assert totals == sorted(totals, reverse=True)
    # รุ่นที่ไม่มีระบบยกหน้ารถต้องไม่ได้ระยะใต้ท้องเพิ่มในการจัดอันดับ
    gtr = next(r for r in data["ranking"] if r["car_id"] == "gtr-r35")
    assert gtr["effective_clearance_mm"] == 110


def test_unknown_car_and_bad_input():
    assert client.post("/api/simulation", json=dict(BASE, car_id="ไม่มีรุ่นนี้")).status_code == 404
    assert client.post("/api/simulation", json=dict(BASE, flood_depth_cm=-5)).status_code == 422
    assert client.post("/api/simulation", json=dict(BASE, traffic_share_pct=150)).status_code == 422
    assert client.post("/api/simulation", json=dict(BASE, road_rough=9)).status_code == 422

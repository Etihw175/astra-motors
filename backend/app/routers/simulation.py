# Router: จำลองการใช้งานจริงบนถนนไทย (น้ำท่วม, ลูกระนาด, หลุมบ่อ, ฝนตก, ค่าน้ำมัน)
# ทุกผลลัพธ์เป็นการประเมินเชิงการศึกษาจากค่าจำลองใน data.py ไม่ใช่ข้อมูลรับรองจากผู้ผลิต
import math

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..crud import car_dict, get_car_or_404
from ..data import THAI_ROAD_PRESETS, TRIP_BKK_CHIANGMAI_KM
from ..database import get_session
from ..models import Car
from ..schemas import SimulationCreate

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

# น้ำหนักของแต่ละสถานการณ์ในคะแนนรวม 100 คะแนน
WEIGHTS = {"flood": 30, "bump": 20, "rough": 20, "fuel": 15, "rain": 15}

USABLE_TANK = 0.9   # ไม่ขับจนน้ำมันหมดถัง เผื่อสำรอง 10%


def _effective_clearance_mm(car: dict, front_lift: bool) -> tuple[int, int]:
    """คืน (ระยะใต้ท้องที่ใช้จริง, ระยะที่ระบบยกหน้าช่วยได้) หน่วยมิลลิเมตร"""
    road = car["road"]
    lift = road["front_lift_mm"] if (front_lift and road["front_lift_mm"]) else 0
    return road["ground_clearance_mm"] + lift, lift


# ---------- แต่ละสถานการณ์: คืน (คะแนน 0-100, ผลตัดสิน, หัวข้อ, คำแนะนำ) ----------

def _flood(car: dict, clearance_mm: int, depth_cm: float) -> dict:
    clearance_cm = clearance_mm / 10
    # เกณฑ์: ปลอดภัยเมื่อน้ำไม่เกินครึ่งหนึ่งของระยะใต้ท้อง เพราะรถวิ่งแล้วน้ำจะยกตัวสูงขึ้น
    safe_cm = clearance_cm * 0.5

    if depth_cm <= 0:
        score, verdict = 100, "ok"
        headline = "ถนนแห้ง ไม่มีข้อจำกัด"
        advice = ["ขับได้ตามปกติ"]
    elif depth_cm <= safe_cm:
        score, verdict = 90, "ok"
        headline = f"ผ่านได้ น้ำ {depth_cm:.0f} ซม. ยังต่ำกว่าครึ่งหนึ่งของระยะใต้ท้อง ({clearance_cm:.0f} ซม.)"
        advice = [
            "ใช้ความเร็วไม่เกิน 20 กม./ชม. เพื่อไม่ให้น้ำถูกดันขึ้นหน้ารถ",
            "เว้นระยะจากคันหน้า อย่าตามคลื่นน้ำที่รถคันอื่นดันมา",
        ]
    elif depth_cm <= clearance_cm:
        score, verdict = 45, "caution"
        headline = f"เสี่ยง น้ำ {depth_cm:.0f} ซม. เกือบเท่าระยะใต้ท้อง ({clearance_cm:.0f} ซม.)"
        advice = [
            "ถ้าเลี่ยงได้ควรเลี่ยง — ชุดแอโรและดิฟฟิวเซอร์ใต้ท้องอาจเสียหาย",
            "ถ้าจำเป็น ให้ขับช้ามาก เลี้ยงคันเร่งนิ่ง ๆ ห้ามหยุดกลางน้ำ",
            "พ้นน้ำแล้วย้ำเบรกเบา ๆ ให้ผ้าเบรกแห้งก่อนใช้ความเร็ว",
        ]
    else:
        score, verdict = 5, "danger"
        headline = f"ห้ามฝ่า น้ำ {depth_cm:.0f} ซม. สูงกว่าระยะใต้ท้อง ({clearance_cm:.0f} ซม.)"
        advice = [
            "ช่องรับอากาศของซูเปอร์คาร์อยู่ต่ำ เสี่ยงน้ำเข้าเครื่องจนเครื่องพัง (hydrolock)",
            "ประกันภัยหลายกรมธรรม์ไม่คุ้มครองความเสียหายจากการฝ่าน้ำท่วมโดยเจตนา",
            "จอดรอในที่สูง หรือเรียกรถยกดีกว่าเสี่ยงค่าซ่อมเครื่องยนต์",
        ]

    if car["road"]["front_lift_mm"] == 0 and depth_cm > safe_cm:
        advice.append("รุ่นนี้ไม่มีระบบยกหน้ารถจากโรงงาน จึงเพิ่มระยะใต้ท้องชั่วคราวไม่ได้")

    return {
        "id": "flood",
        "title": "น้ำท่วมขัง / ฝนตกหนัก",
        "score": score,
        "verdict": verdict,
        "headline": headline,
        "detail": f"ระดับน้ำที่ยังปลอดภัยสำหรับรุ่นนี้คือไม่เกิน {safe_cm:.0f} ซม.",
        "advice": advice,
    }


def _bump(car: dict, clearance_mm: int, lift_mm: int, height_cm: float) -> dict:
    clearance_cm = clearance_mm / 10

    if height_cm <= 0:
        score, verdict = 100, "ok"
        headline = "ไม่มีเนินให้ข้าม"
        advice = ["ขับได้ตามปกติ"]
    elif height_cm <= clearance_cm * 0.75:
        score, verdict = 92, "ok"
        headline = f"ข้ามได้ เนินสูง {height_cm:.0f} ซม. เทียบกับระยะใต้ท้อง {clearance_cm:.0f} ซม."
        advice = ["ลดความเร็วเหลือ 10-15 กม./ชม. ก่อนถึงเนิน"]
    elif height_cm <= clearance_cm:
        score, verdict = 55, "caution"
        headline = f"เฉียดฉิว เนินสูง {height_cm:.0f} ซม. ใกล้เคียงระยะใต้ท้อง {clearance_cm:.0f} ซม."
        advice = [
            "เข้าเนินแบบเฉียง 30-45 องศา ให้ล้อขึ้นทีละข้าง ลดโอกาสสปอยเลอร์หน้าครูด",
            "ให้คนนั่งข้างลงไปดูระยะก่อน ถ้าเป็นเนินที่ไม่คุ้นเคย",
        ]
    else:
        score, verdict = 15, "danger"
        headline = f"ท้องครูดแน่นอน เนินสูง {height_cm:.0f} ซม. เกินระยะใต้ท้อง {clearance_cm:.0f} ซม."
        advice = [
            "หาทางเลี่ยง หรือใช้ทางเข้า-ออกอีกด้านที่ลาดกว่า",
            "ถ้าจำเป็นต้องข้าม ให้ใช้แผ่นไม้/แผ่นยางหนุนลดความชันของเนิน",
        ]

    if lift_mm:
        advice.insert(0, f"เปิดระบบยกหน้ารถแล้ว เพิ่มระยะใต้ท้องอีก {lift_mm} มม. (ใช้ได้ที่ความเร็วต่ำเท่านั้น)")
    elif car["road"]["front_lift_mm"]:
        advice.append(f"รุ่นนี้เลือกติดตั้งระบบยกหน้ารถได้ ช่วยเพิ่มระยะใต้ท้องอีก {car['road']['front_lift_mm']} มม.")

    return {
        "id": "bump",
        "title": "ลูกระนาด / ทางลาดเข้าห้าง",
        "score": score,
        "verdict": verdict,
        "headline": headline,
        "detail": f"ระยะใต้ท้องที่ใช้จริงตอนนี้ {clearance_cm:.1f} ซม.",
        "advice": advice,
    }


def _rough(car: dict, rough: int) -> dict:
    road = car["road"]
    # ยางแก้มเตี้ย + ล้อขอบใหญ่ = โอกาสล้อคด/ยางบวมสูงเมื่อตกหลุม
    fragility = (40 - road["tire_aspect"]) / 10 + max(0, road["wheel_inch"] - 19) * 0.5
    score = max(5, round(100 - rough * (16 + fragility * 7)))

    labels = {
        0: "ทางด่วน/มอเตอร์เวย์ ผิวเรียบ",
        1: "ถนนในเมือง มีรอยปะและฝาท่อ",
        2: "ถนนต่างจังหวัด มีหลุมบ่อ",
        3: "ซอยแคบ ผิวถนนชำรุด",
    }
    verdict = "ok" if score >= 70 else "caution" if score >= 40 else "danger"

    advice = [f"ยางแก้ม {road['tire_aspect']} บนล้อขอบ {road['wheel_inch']} นิ้ว รับแรงกระแทกจากหลุมได้น้อย"]
    if rough >= 1:
        advice.append("เลี่ยงฝาท่อและรอยปะถนน โดยเฉพาะตอนฝนตกที่มองไม่เห็นความลึก")
    if rough >= 2:
        advice.append("ตกหลุมแรง ๆ ครั้งเดียวอาจทำให้ล้อคด — ค่าล้อหนึ่งวงระดับนี้หลักแสน")
    if rough >= 3:
        advice.append("ซอยแคบเลี้ยวกลับลำบาก ควรเช็กเส้นทางก่อนเข้า และระวังขอบฟุตพาทตอนถอย")

    return {
        "id": "rough",
        "title": "ถนนขรุขระ / หลุมบ่อ",
        "score": score,
        "verdict": verdict,
        "headline": f"{labels[rough]} — ความเสี่ยงต่อล้อและยาง {'ต่ำ' if score >= 70 else 'ปานกลาง' if score >= 40 else 'สูง'}",
        "detail": "ประเมินจากความเตี้ยของแก้มยางและขนาดล้อของรุ่นนี้",
        "advice": advice,
    }


def _rain(car: dict) -> dict:
    road = car["road"]
    awd = road["drive_code"] == "awd"
    power = car["power_hp"]

    score = 88 if awd else 62
    if power >= 600:
        score -= 8            # แรงม้าสูงบนถนนลื่นคุมยาก โดยเฉพาะขับหลัง
    score = max(20, min(100, score))
    verdict = "ok" if score >= 70 else "caution"

    advice = []
    if awd:
        advice.append("ระบบขับเคลื่อนสี่ล้อช่วยเรื่องการออกตัวบนถนนเปียกได้มาก")
    else:
        advice.append("ขับเคลื่อนล้อหลัง + แรงม้าสูง ถนนเปียกต้องคุมคันเร่งนุ่ม ๆ ห้ามกดกระชาก")
    advice.append("ยางสมรรถนะสูงจะเกาะดีเมื่อยางร้อน ช่วงเริ่มขับตอนฝนตกให้ระวังเป็นพิเศษ")
    advice.append("ยางแก้มเตี้ยหน้าสัมผัสกว้าง เสี่ยงเหินน้ำ (aquaplaning) ถ้าใช้ความเร็วสูงบนถนนมีน้ำขัง")

    return {
        "id": "rain",
        "title": "ฝนตก / ถนนลื่น",
        "score": score,
        "verdict": verdict,
        "headline": f"{car['drive']} · {power} แรงม้า",
        "detail": "ประเมินจากระบบขับเคลื่อนและแรงม้าเทียบกับสภาพถนนเปียก",
        "advice": advice,
    }


def _fuel(car: dict, km_per_year: int, traffic_share_pct: int, fuel_price: float) -> dict:
    road = car["road"]
    share = traffic_share_pct / 100

    # อัตราสิ้นเปลืองรวมต้องใช้ค่าเฉลี่ยฮาร์มอนิก ไม่ใช่ค่าเฉลี่ยเลขคณิต
    # เพราะสัดส่วนที่ให้มาเป็น "ระยะทาง" ไม่ใช่ "ปริมาณน้ำมัน"
    blended = 1 / (share / road["city_kmpl"] + (1 - share) / road["highway_kmpl"])

    litres_year = km_per_year / blended
    cost_year = litres_year * fuel_price
    tank_range = road["fuel_tank_l"] * USABLE_TANK * blended
    highway_range = road["fuel_tank_l"] * USABLE_TANK * road["highway_kmpl"]
    refuels = max(0, math.ceil(TRIP_BKK_CHIANGMAI_KM / highway_range) - 1)

    # ให้คะแนนแบบเทียบกับกรอบ 3-15 กม./ลิตร (ช่วงที่พบจริงในรถกลุ่มนี้)
    score = max(10, min(100, round((blended - 3) / (15 - 3) * 100)))
    verdict = "ok" if score >= 60 else "caution" if score >= 35 else "danger"

    return {
        "id": "fuel",
        "title": "ค่าน้ำมันในการใช้งานจริง",
        "score": score,
        "verdict": verdict,
        "headline": f"เฉลี่ย {blended:.1f} กม./ลิตร เมื่อวิ่งในเมือง {traffic_share_pct}% ของระยะทาง",
        "detail": f"ค่าน้ำมันประมาณ {round(cost_year / 12):,} บาท/เดือน ({round(cost_year):,} บาท/ปี)",
        "advice": [
            f"ในเมืองรถติดทำได้ราว {road['city_kmpl']} กม./ลิตร · ทางไกลราว {road['highway_kmpl']} กม./ลิตร",
            f"เติมเต็มถัง {road['fuel_tank_l']} ลิตร ({road['fuel_grade']}) วิ่งได้ประมาณ {round(tank_range):,} กม.",
            (f"กรุงเทพฯ–เชียงใหม่ {TRIP_BKK_CHIANGMAI_KM:,} กม. วิ่งถึงได้ในถังเดียว (ถ้าออกจากบ้านแบบเต็มถัง)"
             if refuels == 0 else
             f"กรุงเทพฯ–เชียงใหม่ {TRIP_BKK_CHIANGMAI_KM:,} กม. ต้องแวะเติมระหว่างทางประมาณ {refuels} ครั้ง"),
        ],
        "numbers": {
            "city_kmpl": road["city_kmpl"],
            "highway_kmpl": road["highway_kmpl"],
            "blended_kmpl": round(blended, 2),
            "litres_per_year": round(litres_year),
            "cost_per_year": round(cost_year),
            "cost_per_month": round(cost_year / 12),
            "tank_range_km": round(tank_range),
            "refuel_stops_bkk_chiangmai": refuels,
        },
    }


def _grade(total: int) -> dict:
    if total >= 80:
        return {"letter": "A", "label": "ใช้งานประจำวันบนถนนไทยได้สบาย"}
    if total >= 65:
        return {"letter": "B", "label": "ใช้ได้ แต่ต้องเลือกเส้นทางบ้าง"}
    if total >= 45:
        return {"letter": "C", "label": "ใช้เป็นรถคันที่สอง เลี่ยงเส้นทางเสี่ยง"}
    return {"letter": "D", "label": "เก็บไว้ขับวันอากาศดี ไม่เหมาะกับสภาพนี้"}


def _evaluate(car: dict, body: SimulationCreate) -> dict:
    clearance_mm, lift_mm = _effective_clearance_mm(car, body.front_lift)

    scenarios = [
        _flood(car, clearance_mm, body.flood_depth_cm),
        _bump(car, clearance_mm, lift_mm, body.bump_height_cm),
        _rough(car, body.road_rough),
        _rain(car),
        _fuel(car, body.km_per_year, body.traffic_share_pct, body.fuel_price),
    ]
    by_id = {s["id"]: s for s in scenarios}
    total = round(sum(by_id[key]["score"] * weight for key, weight in WEIGHTS.items()) / sum(WEIGHTS.values()))

    return {
        "scenarios": scenarios,
        "total": total,
        "breakdown": {key: by_id[key]["score"] for key in WEIGHTS},
        "clearance": {
            "base_mm": car["road"]["ground_clearance_mm"],
            "lift_mm": lift_mm,
            "effective_mm": clearance_mm,
            "front_lift_available": car["road"]["front_lift_mm"] > 0,
            "front_lift_active": lift_mm > 0,
        },
    }


@router.get("/conditions", summary="ตัวเลือกสถานการณ์สำหรับหน้าจำลอง")
def conditions():
    """คืนชุดสถานการณ์ถนนไทยที่เลือกได้ + ค่าเริ่มต้นของฟอร์ม (ไม่ต้องล็อกอิน)"""
    return THAI_ROAD_PRESETS


@router.post("", summary="จำลองการใช้งานรถรุ่นที่เลือกบนถนนไทย")
def simulate(body: SimulationCreate, db: Session = Depends(get_session)):
    """ประเมิน 5 ด้าน: น้ำท่วม, ลูกระนาด, หลุมบ่อ, ฝนตก และค่าน้ำมัน

    พร้อมจัดอันดับรถทุกรุ่นภายใต้เงื่อนไขเดียวกัน เพื่อให้เทียบกันได้ตรง ๆ
    """
    car = car_dict(get_car_or_404(db, body.car_id))
    result = _evaluate(car, body)

    if body.front_lift and not result["clearance"]["front_lift_available"]:
        note = f"{car['name']} ไม่มีระบบยกหน้ารถ จึงคำนวณจากระยะใต้ท้องมาตรฐาน"
    else:
        note = None

    # จัดอันดับทุกรุ่นด้วยเงื่อนไขชุดเดียวกัน (รุ่นที่ไม่มีระบบยกหน้าจะไม่ได้ระยะเพิ่ม)
    ranking = []
    for other in (car_dict(c) for c in db.exec(select(Car)).all()):
        scored = _evaluate(other, body.model_copy(update={"car_id": other["id"]}))
        ranking.append({
            "car_id": other["id"],
            "name": other["name"],
            "total": scored["total"],
            "effective_clearance_mm": scored["clearance"]["effective_mm"],
            "blended_kmpl": next(s for s in scored["scenarios"] if s["id"] == "fuel")["numbers"]["blended_kmpl"],
        })
    ranking.sort(key=lambda r: r["total"], reverse=True)

    return {
        "car": {"id": car["id"], "name": car["name"], "drive": car["drive"]},
        "conditions": body.model_dump(),
        "clearance": result["clearance"],
        "scenarios": result["scenarios"],
        "score": {
            "total": result["total"],
            "breakdown": result["breakdown"],
            "weights": WEIGHTS,
            "grade": _grade(result["total"]),
        },
        "ranking": ranking,
        "note": note,
        "disclaimer": "ผลลัพธ์เป็นการประเมินเชิงการศึกษาจากค่าจำลอง ไม่ใช่ข้อมูลรับรองจากผู้ผลิต",
    }
